"""Calculated sensors for Smart EV Charging."""

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .const import CHARGING_STATUSES
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up calculated sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            SmartEVCurrentSOCSensor(runtime),
            SmartEVRequiredBatteryEnergySensor(runtime),
            SmartEVRequiredGridEnergySensor(runtime),
            SmartEVRequiredChargeTimeSensor(runtime),
            SmartEVLatestStartSensor(runtime),
            SmartEVStatusSensor(runtime),
            SmartEVRequestedPowerSensor(runtime),
        ]
    )


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
