"""Serialized charger control through user-selected Home Assistant scripts."""
from __future__ import annotations

import asyncio
import logging
import math

_LOGGER = logging.getLogger(__name__)


def requested_current(power: float, phases: int) -> int | None:
    """Never exceed requested power; below the IEC minimum means no charging."""
    if phases not in (1, 3) or not math.isfinite(power) or power <= 0:
        return None
    current = min(16, math.floor(power / (230 * phases)))
    return current if current >= 6 else None


class ChargerControl:
    """Own only sessions started here; never take over manual charging."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.task = None
        self.closed = False
        self.dirty = False
        self.owned = False
        self.current = None
        self.stop_entity = None
        self.binding = None

    def cancel(self):
        """Prevent pending work from issuing commands after unload."""
        self.closed = True
        if self.task:
            self.task.cancel()

    def schedule(self):
        if self.closed:
            return
        self.dirty = True
        if self.task is None or self.task.done():
            self.task = self.runtime.hass.async_create_task(self._run())

    def _configuration(self):
        return dict(self.runtime.entry.options)

    def _desired(self, options):
        r = self.runtime
        if options.get("charger_control_enabled") is not True:
            return None
        soc = r.current_soc
        target = r.target_soc
        if (soc is None or not math.isfinite(soc) or not 0 <= soc <= 100
                or not math.isfinite(target) or not 0 <= target <= 100
                or soc >= target or r.charger_connected is not True):
            return None
        for key in ("charger_start_entity", "charger_stop_entity", "charger_limit_entity"):
            entity = options.get(key)
            if not entity or not entity.startswith("script."):
                return None
            state = r.hass.states.get(entity)
            if state is None or state.state not in ("on", "off"):
                return None
            if not r.hass.services.has_service("script", entity.split(".", 1)[1]):
                return None
        for key in ("charger_status_entity", "charger_power_entity", "charger_current_entity", "charger_session_energy_entity"):
            entity = options.get(key)
            if entity:
                state = r.hass.states.get(entity)
                if state is None or state.state in ("unknown", "unavailable"):
                    return None
                if key != "charger_status_entity":
                    try:
                        value = float(state.state)
                    except (TypeError, ValueError):
                        return None
                    if not math.isfinite(value) or value < 0:
                        return None
        if not (r.preferred_charge_now or r.must_charge_now):
            return None
        return requested_current(r.requested_power_w, options.get("charger_phases", 1))

    async def _call(self, entity, data=None):
        domain, service = entity.split(".", 1)
        await self.runtime.hass.services.async_call(
            domain, service, data or {}, blocking=True
        )

    async def _stop(self):
        if self.owned:
            await self._call(self.stop_entity)
            self.owned = False
            self.current = None

    async def _run(self):
        while self.dirty and not self.closed:
            self.dirty = False
            try:
                options = self._configuration()
                current = self._desired(options)
                if current is None:
                    # Disabled is an absolute no-command gate. Remember ownership
                    # so a subsequent explicit enable can reconcile the session.
                    if options.get("charger_control_enabled") is True:
                        await self._stop()
                    continue
                binding = tuple(options.get(key) for key in ("charger_start_entity", "charger_stop_entity", "charger_limit_entity", "charger_phases"))
                if binding != self.binding:
                    await self._stop()
                    if self.closed or self._configuration().get("charger_control_enabled") is not True:
                        return
                    self.current = None
                    self.binding = binding
                    if options != self._configuration() or self._desired(options) != current:
                        self.dirty = True
                        continue
                if self.current != current:
                    await self._call(options["charger_limit_entity"], {"current": current})
                    # Inputs may change while the service is awaited.
                    if self.closed:
                        return
                    if options != self._configuration() or self._desired(options) != current:
                        self.dirty = True
                        continue
                    self.current = current
                if not self.owned:
                    self.stop_entity = options["charger_stop_entity"]
                    # A failed start might still have reached the charger.
                    self.owned = True
                    await self._call(options["charger_start_entity"])
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Charger control failed; no further start/current command this cycle")
                self.current = None
                if self._configuration().get("charger_control_enabled") is True:
                    try:
                        await self._stop()
                    except Exception:
                        _LOGGER.exception("Fail-safe charger stop failed; retry on next update")
                # Avoid an immediate retry loop caused by script state changes.
                self.dirty = False
