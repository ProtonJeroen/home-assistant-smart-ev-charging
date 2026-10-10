"""Calculated sensors for Smart EV Charging."""

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .const import CHARGING_STATUSES
from .charger_control import CONTROL_STATUSES
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up calculated sensors."""
    runtime = entry.runtime_data
    entities: list[SensorEntity] = [
        SmartEVCurrentSOCSensor(runtime),
        SmartEVRequiredBatteryEnergySensor(runtime),
        SmartEVRequiredGridEnergySensor(runtime),
        SmartEVRequiredChargeTimeSensor(runtime),
        SmartEVLatestStartSensor(runtime),
        SmartEVStatusSensor(runtime),
        SmartEVControlStatusSensor(runtime),
        SmartEVRequestedPowerSensor(runtime),
        SmartEVCurrentChargeStartSensor(runtime),
        SmartEVCurrentChargeEndSensor(runtime),
        SmartEVNextChargeStartSensor(runtime),
        SmartEVChargingPlanSensor(runtime),
        SmartEVPlannedChargeMinutesSensor(runtime),
        SmartEVEstimatedChargeCostSensor(runtime),
        SmartEVAverageChargePriceSensor(runtime),
    ]

    if runtime.price_entity_id:
        entities.append(SmartEVPriceChartSensor(runtime))
    if runtime.charger_status_entity_id:
        entities.append(SmartEVChargerStatusSensor(runtime))
    if runtime.charger_power_entity_id:
        entities.append(SmartEVChargerPowerSensor(runtime))
    if runtime.charger_current_entity_id:
        entities.append(SmartEVChargerCurrentSensor(runtime))
    if runtime.charger_session_energy_entity_id:
        entities.append(SmartEVChargerSessionEnergySensor(runtime))

    async_add_entities(entities)


class SmartEVCurrentSOCSensor(SmartEVChargingEntity, SensorEntity):
    """Normalized current vehicle SOC."""

    _attr_translation_key = "current_soc"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "current_soc")

    @property
    def available(self) -> bool:
        return self.runtime.current_soc is not None

    @property
    def native_value(self) -> float | None:
        return self.runtime.current_soc


class SmartEVRequiredBatteryEnergySensor(SmartEVChargingEntity, SensorEntity):
    """Energy that must be added to the traction battery."""

    _attr_translation_key = "required_battery_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "required_battery_energy")

    @property
    def available(self) -> bool:
        return self.runtime.charging_estimate is not None

    @property
    def native_value(self) -> float | None:
        estimate = self.runtime.charging_estimate
        return None if estimate is None else round(estimate.battery_energy_kwh, 3)


class SmartEVRequiredGridEnergySensor(SmartEVChargingEntity, SensorEntity):
    """Grid energy required after charging losses."""

    _attr_translation_key = "required_grid_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "required_grid_energy")

    @property
    def available(self) -> bool:
        return self.runtime.charging_estimate is not None

    @property
    def native_value(self) -> float | None:
        estimate = self.runtime.charging_estimate
        return None if estimate is None else round(estimate.grid_energy_kwh, 3)


class SmartEVRequiredChargeTimeSensor(SmartEVChargingEntity, SensorEntity):
    """Estimated charging duration."""

    _attr_translation_key = "required_charge_time"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "required_charge_time")

    @property
    def available(self) -> bool:
        return self.runtime.charging_estimate is not None

    @property
    def native_value(self) -> float | None:
        estimate = self.runtime.charging_estimate
        return None if estimate is None else round(estimate.duration_minutes, 1)


class SmartEVLatestStartSensor(SmartEVChargingEntity, SensorEntity):
    """Latest possible start time to meet the configured departure."""

    _attr_translation_key = "latest_start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "latest_start")

    @property
    def available(self) -> bool:
        return self.runtime.latest_start is not None

    @property
    def native_value(self) -> datetime | None:
        return self.runtime.latest_start


class SmartEVStatusSensor(SmartEVChargingEntity, SensorEntity):
    """Human-readable charging strategy status."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = CHARGING_STATUSES

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "status")

    @property
    def native_value(self) -> str:
        return self.runtime.status


class SmartEVRequestedPowerSensor(SmartEVChargingEntity, SensorEntity):
    """Power requested from the Home Energy Manager."""

    _attr_translation_key = "requested_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "requested_power")

    @property
    def native_value(self) -> int:
        return self.runtime.requested_power_w


class SmartEVCurrentChargeStartSensor(SmartEVChargingEntity, SensorEntity):
    """Start of the currently active smart-charge slot."""

    _attr_translation_key = "current_charge_start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "current_charge_start")

    @property
    def available(self) -> bool:
        return self.runtime.current_charge_start is not None

    @property
    def native_value(self) -> datetime | None:
        return self.runtime.current_charge_start


class SmartEVCurrentChargeEndSensor(SmartEVChargingEntity, SensorEntity):
    """End of the currently active smart-charge slot."""

    _attr_translation_key = "current_charge_end"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "current_charge_end")

    @property
    def available(self) -> bool:
        return self.runtime.current_charge_end is not None

    @property
    def native_value(self) -> datetime | None:
        return self.runtime.current_charge_end


class SmartEVNextChargeStartSensor(SmartEVChargingEntity, SensorEntity):
    """Next selected smart-charge interval."""

    _attr_translation_key = "next_charge_start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "next_charge_start")

    @property
    def available(self) -> bool:
        return self.runtime.next_charge_start is not None

    @property
    def native_value(self) -> datetime | None:
        return self.runtime.next_charge_start


class SmartEVChargingPlanSensor(SmartEVChargingEntity, SensorEntity):
    """Selected smart charging plan with all slots in attributes."""

    _attr_translation_key = "charging_plan"
    _attr_suggested_display_precision = 0

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charging_plan")

    @property
    def available(self) -> bool:
        return self.runtime.planned_slot_count is not None

    @property
    def native_value(self) -> int | None:
        return self.runtime.planned_slot_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.runtime.plan_attributes


class SmartEVPlannedChargeMinutesSensor(SmartEVChargingEntity, SensorEntity):
    """Total selected charging minutes in the smart plan."""

    _attr_translation_key = "planned_charge_minutes"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "planned_charge_minutes")

    @property
    def available(self) -> bool:
        return self.runtime.planned_minutes is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.planned_minutes
        return None if value is None else round(value, 1)


class SmartEVEstimatedChargeCostSensor(SmartEVChargingEntity, SensorEntity):
    """Estimated electricity cost of the selected smart plan."""

    _attr_translation_key = "estimated_charge_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "estimated_charge_cost")

    @property
    def available(self) -> bool:
        return self.runtime.estimated_charge_cost is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.estimated_charge_cost
        return None if value is None else round(value, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.runtime.plan_attributes


class SmartEVAverageChargePriceSensor(SmartEVChargingEntity, SensorEntity):
    """Energy-weighted average electricity price of the selected plan."""

    _attr_translation_key = "average_charge_price"
    _attr_native_unit_of_measurement = (
        f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}"
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "average_charge_price")

    @property
    def available(self) -> bool:
        return self.runtime.average_charge_price is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.average_charge_price
        return None if value is None else round(value, 5)


class SmartEVPriceChartSensor(SmartEVChargingEntity, SensorEntity):
    """Chart-ready price and smart-charge plan data."""

    _attr_translation_key = "price_chart"

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "price_chart")

    @property
    def available(self) -> bool:
        return bool(self.runtime.price_chart_bars)

    @property
    def native_value(self) -> int:
        return len(self.runtime.price_chart_bars)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "bars": self.runtime.price_chart_bars,
            "price_source": self.runtime.price_entity_id,
        }


class SmartEVChargerStatusSensor(SmartEVChargingEntity, SensorEntity):
    """Read-only normalized charger status."""

    _attr_translation_key = "charger_status"

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charger_status")

    @property
    def available(self) -> bool:
        return self.runtime.charger_status is not None

    @property
    def native_value(self) -> str | None:
        return self.runtime.charger_status


class SmartEVChargerPowerSensor(SmartEVChargingEntity, SensorEntity):
    """Read-only charger power normalized to watts."""

    _attr_translation_key = "charger_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charger_power")

    @property
    def available(self) -> bool:
        return self.runtime.charger_power_w is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.charger_power_w
        return None if value is None else round(value, 1)


class SmartEVChargerCurrentSensor(SmartEVChargingEntity, SensorEntity):
    """Read-only charger current normalized to amperes."""

    _attr_translation_key = "charger_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charger_current")

    @property
    def available(self) -> bool:
        return self.runtime.charger_current_a is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.charger_current_a
        return None if value is None else round(value, 2)


class SmartEVChargerSessionEnergySensor(SmartEVChargingEntity, SensorEntity):
    """Read-only charger session energy normalized to kWh."""

    _attr_translation_key = "charger_session_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charger_session_energy")

    @property
    def available(self) -> bool:
        return self.runtime.charger_session_energy_kwh is not None

    @property
    def native_value(self) -> float | None:
        value = self.runtime.charger_session_energy_kwh
        return None if value is None else round(value, 3)


class SmartEVControlStatusSensor(SmartEVChargingEntity, SensorEntity):
    """Explain the control gate independently of the charging strategy."""

    _attr_translation_key = "charger_control_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(CONTROL_STATUSES)

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charger_control_status")

    @property
    def native_value(self) -> str:
        return self.runtime.control.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        control = self.runtime.control
        return {
            "strategy_status": self.runtime.status,
            "requested_power_w": self.runtime.requested_power_w,
            "applied_current_a": control.current,
            "session_owned": control.owned,
            "next_charge_start": self.runtime.next_charge_start,
        }
