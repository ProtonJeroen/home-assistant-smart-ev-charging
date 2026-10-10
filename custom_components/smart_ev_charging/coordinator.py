"""Runtime state and calculations for Smart EV Charging."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_CHARGE_EFFICIENCY,
    CONF_CHARGE_POWER_KW,
    CONF_CHARGING_MODE,
    CONF_DEPARTURE,
    CONF_SAFETY_MARGIN_MINUTES,
    CONF_SOC_ENTITY,
    CONF_TARGET_SOC,
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_CHARGE_POWER_KW,
    DEFAULT_CHARGING_MODE,
    DEFAULT_SAFETY_MARGIN_MINUTES,
    DEFAULT_TARGET_SOC,
    MODE_CHARGE_NOW,
    MODE_OFF,
    MODE_READY_BY_DEPARTURE,
    MODE_SMART,
    STATUS_CHARGE_NOW,
    STATUS_DEPARTURE_NOT_SET,
    STATUS_MUST_CHARGE_DEADLINE,
    STATUS_OFF,
    STATUS_TARGET_REACHED,
    STATUS_VEHICLE_DATA_UNAVAILABLE,
    STATUS_WAITING_FOR_LATEST_START,
    STATUS_WAITING_FOR_PRICE_DATA,
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
            CONF_SAFETY_MARGIN_MINUTES: float(
                entry.options.get(
                    CONF_SAFETY_MARGIN_MINUTES, DEFAULT_SAFETY_MARGIN_MINUTES
                )
            ),
            CONF_CHARGING_MODE: str(
                entry.options.get(CONF_CHARGING_MODE, DEFAULT_CHARGING_MODE)
            ),
        }

    async def async_start(self) -> None:
        """Listen for source SOC changes and deadline transitions."""
        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self.entry.data[CONF_SOC_ENTITY]],
                self._async_soc_changed,
            )
        )
        self.entry.async_on_unload(
            async_track_time_interval(
                self.hass,
                self._async_time_changed,
                timedelta(minutes=1),
            )
        )

    @callback
    def _async_soc_changed(self, event: Event) -> None:
        self._notify()

    @callback
    def _async_time_changed(self, now: datetime) -> None:
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
    def safety_margin_minutes(self) -> float:
        return float(self._settings[CONF_SAFETY_MARGIN_MINUTES])

    @property
    def charging_mode(self) -> str:
        return str(self._settings[CONF_CHARGING_MODE])

    @property
    def departure(self) -> datetime | None:
        value = self._settings.get(CONF_DEPARTURE)
        return dt_util.parse_datetime(str(value)) if value else None

    @property
    def target_reached(self) -> bool:
        soc = self.current_soc
        return soc is not None and soc >= self.target_soc

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
        return departure - timedelta(
            minutes=estimate.duration_minutes + self.safety_margin_minutes
        )

    @property
    def must_charge_now(self) -> bool:
        """Return whether charging can no longer safely be delayed."""
        if self.charging_mode == MODE_OFF or self.target_reached:
            return False

        if self.charging_mode == MODE_CHARGE_NOW:
            return True

        latest_start = self.latest_start
        if latest_start is None:
            return False

        return dt_util.now() >= latest_start

    @property
    def preferred_charge_now(self) -> bool:
        """Return whether the current strategy prefers charging right now.

        Smart-price preference will be added by the price planner. Until then,
        Smart mode only requests charging when the deadline becomes mandatory.
        """
        if self.charging_mode == MODE_OFF or self.target_reached:
            return False

        if self.charging_mode == MODE_CHARGE_NOW:
            return True

        return self.must_charge_now

    @property
    def requested_power_w(self) -> int:
        """Return requested charging power for the Home Energy Manager."""
        if not (self.preferred_charge_now or self.must_charge_now):
            return 0
        return round(self.charge_power_kw * 1000)

    @property
    def status(self) -> str:
        """Return a stable strategy status for the UI and HEM."""
        if self.charging_mode == MODE_OFF:
            return STATUS_OFF

        if self.current_soc is None:
            return STATUS_VEHICLE_DATA_UNAVAILABLE

        if self.target_reached:
            return STATUS_TARGET_REACHED

        if self.charging_mode == MODE_CHARGE_NOW:
            return STATUS_CHARGE_NOW

        if self.departure is None:
            return STATUS_DEPARTURE_NOT_SET

        if self.must_charge_now:
            return STATUS_MUST_CHARGE_DEADLINE

        if self.charging_mode == MODE_SMART:
            return STATUS_WAITING_FOR_PRICE_DATA

        if self.charging_mode == MODE_READY_BY_DEPARTURE:
            return STATUS_WAITING_FOR_LATEST_START

        return STATUS_OFF

    @callback
    def set_setting(
        self, key: str, value: float | str | datetime | None
    ) -> None:
        stored = value.isoformat() if isinstance(value, datetime) else value
        self._settings[key] = stored

        options = dict(self.entry.options)
        if stored is None:
            options.pop(key, None)
        else:
            options[key] = stored

        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self._notify()
