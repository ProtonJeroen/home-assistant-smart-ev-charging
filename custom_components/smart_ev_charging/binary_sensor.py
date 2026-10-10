"""Binary sensors for Smart EV Charging."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Smart EV Charging binary sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            SmartEVPreferredChargeNowBinarySensor(runtime),
            SmartEVMustChargeNowBinarySensor(runtime),
        ]
    )


class SmartEVPreferredChargeNowBinarySensor(
    SmartEVChargingEntity, BinarySensorEntity
):
    """Whether the active strategy prefers charging right now."""

    _attr_translation_key = "preferred_charge_now"

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "preferred_charge_now")

    @property
    def is_on(self) -> bool:
        return self.runtime.preferred_charge_now


class SmartEVMustChargeNowBinarySensor(SmartEVChargingEntity, BinarySensorEntity):
    """Whether charging can no longer safely be delayed."""

    _attr_translation_key = "must_charge_now"

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "must_charge_now")

    @property
    def is_on(self) -> bool:
        return self.runtime.must_charge_now
