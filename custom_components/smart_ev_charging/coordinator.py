"""Runtime state and calculations for Smart EV Charging."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

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
    CONF_PRICE_ENTITY,
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
    PRICE_ATTRIBUTE,
    STATUS_CHARGE_NOW,
    STATUS_DEPARTURE_NOT_SET,
    STATUS_MUST_CHARGE_DEADLINE,
    STATUS_OFF,
    STATUS_PRICE_SOURCE_NOT_CONFIGURED,
    STATUS_SMART_CHARGE_SLOT,
    STATUS_TARGET_REACHED,
    STATUS_VEHICLE_DATA_UNAVAILABLE,
    STATUS_WAITING_FOR_LATEST_START,
    STATUS_WAITING_FOR_PRICE_DATA,
    STATUS_WAITING_FOR_SMART_SLOT,
)
from .models import ChargingEstimate, ChargingPlan, ChargingRequest
from .planner import calculate_charging_estimate, calculate_smart_plan
from .price import parse_price_slots


class SmartEVChargingRuntime:
    """Runtime data for one configured vehicle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._listeners: set[Callable[[], None]] = set()
        self._tracked_price_entity_id = self._configured_price_entity_id()
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
        """Listen for source changes and time-based strategy transitions."""
        tracked_entities = [self.entry.data[CONF_SOC_ENTITY]]
        if self._tracked_price_entity_id:
            tracked_entities.append(self._tracked_price_entity_id)

        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                tracked_entities,
                self._async_source_changed,
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
    def _async_source_changed(self, event: Event) -> None:
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

    def _configured_price_entity_id(self) -> str | None:
        """Return the currently configured generic price source entity."""
        value = self.entry.options.get(
            CONF_PRICE_ENTITY,
            self.entry.data.get(CONF_PRICE_ENTITY),
        )
        return str(value) if value else None

    @property
    def price_entity_id(self) -> str | None:
        """Return the currently configured generic price source entity."""
        return self._configured_price_entity_id()

    @property
    def tracked_price_entity_id(self) -> str | None:
        """Return the price entity currently registered for state tracking."""
        return self._tracked_price_entity_id

    @property
    def departure(self) -> datetime | None:
        value = self._settings.get(CONF_DEPARTURE)
        return dt_util.parse_datetime(str(value)) if value else None

    @property
    def target_ready_time(self) -> datetime | None:
        """Return the time by which charging should be finished."""
        departure = self.departure
        if departure is None:
            return None
        return departure - timedelta(minutes=self.safety_margin_minutes)

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
        ready_time = self.target_ready_time
        if estimate is None or ready_time is None:
            return None
        return ready_time - timedelta(minutes=estimate.duration_minutes)

    @property
    def price_slots(self):
        """Return normalized price slots from the selected HA entity."""
        entity_id = self.price_entity_id
        if not entity_id:
            return ()

        state = self.hass.states.get(entity_id)
        if state is None:
            return ()

        timezone = (
            dt_util.get_time_zone(self.hass.config.time_zone)
            or dt_util.DEFAULT_TIME_ZONE
        )
        return parse_price_slots(
            state.attributes.get(PRICE_ATTRIBUTE),
            timezone,
        )

    @property
    def smart_plan(self) -> ChargingPlan | None:
        """Return the cheapest charge plan for the known price horizon."""
        estimate = self.charging_estimate
        ready_time = self.target_ready_time
        if estimate is None or ready_time is None or not self.price_entity_id:
            return None

        now = dt_util.now()
        if ready_time <= now:
            return None

        return calculate_smart_plan(
            self.price_slots,
            now,
            ready_time,
            estimate.duration_minutes,
            self.charge_power_kw,
        )

    @property
    def smart_plan_ready(self) -> bool:
        """Return whether the plan has complete price coverage and enough time."""
        plan = self.smart_plan
        if plan is None:
            return False

        return (
            plan.coverage_complete
            and plan.planned_minutes + 0.1 >= plan.required_minutes
        )

    @property
    def next_charge_start(self) -> datetime | None:
        """Return the next selected smart-charge slot start."""
        if not self.smart_plan_ready:
            return None

        plan = self.smart_plan
        if plan is None:
            return None

        now = dt_util.now()
        return next((slot.start for slot in plan.slots if slot.end > now), None)

    @property
    def estimated_charge_cost(self) -> float | None:
        """Return estimated grid-energy cost for the smart plan."""
        if not self.smart_plan_ready:
            return None
        plan = self.smart_plan
        return plan.estimated_cost if plan is not None else None

    @property
    def average_charge_price(self) -> float | None:
        """Return energy-weighted average price of the smart plan."""
        if not self.smart_plan_ready:
            return None
        plan = self.smart_plan
        return plan.average_price if plan is not None else None

    @property
    def plan_attributes(self) -> dict[str, Any]:
        """Return diagnostic and dashboard attributes for the smart plan."""
        plan = self.smart_plan
        if plan is None:
            return {
                "price_source": self.price_entity_id,
                "coverage_complete": False,
                "slots": [],
            }

        return {
            "price_source": self.price_entity_id,
            "coverage_complete": plan.coverage_complete,
            "required_minutes": round(plan.required_minutes, 1),
            "planned_minutes": round(plan.planned_minutes, 1),
            "slots": [
                {
                    "from": slot.start.isoformat(),
                    "till": slot.end.isoformat(),
                    "price": round(slot.price, 5),
                    "minutes": round(slot.minutes, 1),
                    "energy_kwh": round(slot.energy_kwh, 3),
                    "cost": round(slot.cost, 3),
                }
                for slot in plan.slots
            ],
        }

    @property
    def must_charge_now(self) -> bool:
        """Return whether charging can no longer safely be delayed."""
        if (
            self.charging_mode == MODE_OFF
            or self.current_soc is None
            or self.target_reached
        ):
            return False

        if self.charging_mode == MODE_CHARGE_NOW:
            return True

        latest_start = self.latest_start
        if latest_start is None:
            return False

        return dt_util.now() >= latest_start

    @property
    def preferred_charge_now(self) -> bool:
        """Return whether the active strategy prefers charging right now."""
        if (
            self.charging_mode == MODE_OFF
            or self.current_soc is None
            or self.target_reached
        ):
            return False

        if self.charging_mode == MODE_CHARGE_NOW:
            return True

        if self.must_charge_now:
            return True

        if self.charging_mode != MODE_SMART or not self.smart_plan_ready:
            return False

        plan = self.smart_plan
        if plan is None:
            return False

        now = dt_util.now()
        return any(slot.start <= now < slot.end for slot in plan.slots)

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
            if not self.price_entity_id:
                return STATUS_PRICE_SOURCE_NOT_CONFIGURED
            if not self.smart_plan_ready:
                return STATUS_WAITING_FOR_PRICE_DATA
            if self.preferred_charge_now:
                return STATUS_SMART_CHARGE_SLOT
            return STATUS_WAITING_FOR_SMART_SLOT

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
