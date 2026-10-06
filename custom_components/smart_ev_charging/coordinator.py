"""Runtime state and calculations for Smart EV Charging."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_CHARGE_EFFICIENCY,
    CONF_CHARGE_POWER_KW,
    CONF_DEPARTURE,
    CONF_SOC_ENTITY,
    CONF_TARGET_SOC,
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_CHARGE_POWER_KW,
    DEFAULT_TARGET_SOC,
)
from .models import ChargingEstimate, ChargingRequest
from .planner import calculate_charging_estimate


class SmartEVChargingRuntime:
    """Runtime data for one configured vehicle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._listeners: set[Callable[[], None]] = set()
        self._settings: dict[str, float | str | None] = {
            CONF_TARGET_SOC: float(
                entry.options.get(CONF_TARGET_SOC, DEFAULT_TARGET_SOC)
            ),
            CONF_CHARGE_POWER_KW: float(
                entry.options.get(CONF_CHARGE_POWER_KW, DEFAULT_CHARGE_POWER_KW)
            ),
            CONF_CHARGE_EFFICIENCY: float(
                entry.options.get(
                    CONF_CHARGE_EFFICIENCY, DEFAULT_CHARGE_EFFICIENCY
                )
            ),
            CONF_DEPARTURE: entry.options.get(CONF_DEPARTURE),
        }

    async def async_start(self) -> None:
        """Listen for source SOC changes."""
        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self.entry.data[CONF_SOC_ENTITY]],
                self._async_soc_changed,
            )
        )

    @callback
    def _async_soc_changed(self, event: Event) -> None:
        self._notify()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        @callback
        def remove() -> None:
            self._listeners.discard(listener)

        return remove

    @callback
    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    @property
    def current_soc(self) -> float | None:
        state = self.hass.states.get(self.entry.data[CONF_SOC_ENTITY])
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        return value if 0 <= value <= 100 else None

    @property
    def battery_capacity_kwh(self) -> float:
        return float(self.entry.data[CONF_BATTERY_CAPACITY_KWH])

    @property
    def target_soc(self) -> float:
        return float(self._settings[CONF_TARGET_SOC])

    @property
    def charge_power_kw(self) -> float:
        return float(self._settings[CONF_CHARGE_POWER_KW])

    @property
    def charge_efficiency(self) -> float:
        return float(self._settings[CONF_CHARGE_EFFICIENCY])

    @property
    def departure(self) -> datetime | None:
        value = self._settings.get(CONF_DEPARTURE)
        return dt_util.parse_datetime(str(value)) if value else None

    @property
    def charging_estimate(self) -> ChargingEstimate | None:
        soc = self.current_soc
        if soc is None:
            return None
        return calculate_charging_estimate(
            ChargingRequest(
                current_soc=soc,
                target_soc=self.target_soc,
                usable_capacity_kwh=self.battery_capacity_kwh,
                charge_power_kw=self.charge_power_kw,
                efficiency=self.charge_efficiency / 100.0,
            )
        )

    @property
    def latest_start(self) -> datetime | None:
        estimate = self.charging_estimate
        departure = self.departure
        if estimate is None or departure is None:
            return None
        return departure - timedelta(minutes=estimate.duration_minutes)

    @callback
    def set_setting(self, key: str, value: float | datetime | None) -> None:
        stored = value.isoformat() if isinstance(value, datetime) else value
        self._settings[key] = stored

        options = dict(self.entry.options)
        if stored is None:
            options.pop(key, None)
        else:
            options[key] = stored

        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self._notify()
