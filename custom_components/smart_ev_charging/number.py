"""Number entities for Smart EV Charging."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .const import (
    CONF_CHARGE_EFFICIENCY,
    CONF_CHARGE_POWER_KW,
    CONF_SAFETY_MARGIN_MINUTES,
    CONF_TARGET_SOC,
)
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up charging settings."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            SmartEVTargetSOCNumber(runtime),
            SmartEVChargePowerNumber(runtime),
            SmartEVChargeEfficiencyNumber(runtime),
            SmartEVSafetyMarginNumber(runtime),
        ]
    )


class SmartEVTargetSOCNumber(SmartEVChargingEntity, NumberEntity):
    """Target state of charge."""

    _attr_translation_key = "target_soc"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 10.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "target_soc")

    @property
    def native_value(self) -> float:
        return self.runtime.target_soc

    async def async_set_native_value(self, value: float) -> None:
        self.runtime.set_setting(CONF_TARGET_SOC, value)


class SmartEVChargePowerNumber(SmartEVChargingEntity, NumberEntity):
    """Expected AC charging power."""

    _attr_translation_key = "charge_power"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.5
    _attr_native_max_value = 22.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_mode = NumberMode.BOX

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charge_power")

    @property
    def native_value(self) -> float:
        return self.runtime.charge_power_kw

    async def async_set_native_value(self, value: float) -> None:
        self.runtime.set_setting(CONF_CHARGE_POWER_KW, value)


class SmartEVChargeEfficiencyNumber(SmartEVChargingEntity, NumberEntity):
    """Expected grid-to-battery efficiency."""

    _attr_translation_key = "charge_efficiency"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 50.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charge_efficiency")

    @property
    def native_value(self) -> float:
        return self.runtime.charge_efficiency

    async def async_set_native_value(self, value: float) -> None:
        self.runtime.set_setting(CONF_CHARGE_EFFICIENCY, value)


class SmartEVSafetyMarginNumber(SmartEVChargingEntity, NumberEntity):
    """Extra time reserved before the requested departure."""

    _attr_translation_key = "safety_margin"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.0
    _attr_native_max_value = 180.0
    _attr_native_step = 5.0
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "safety_margin")

    @property
    def native_value(self) -> float:
        return self.runtime.safety_margin_minutes

    async def async_set_native_value(self, value: float) -> None:
        self.runtime.set_setting(CONF_SAFETY_MARGIN_MINUTES, value)
