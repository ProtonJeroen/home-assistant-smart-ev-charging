"""Select entities for Smart EV Charging."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .const import CHARGING_MODES, CONF_CHARGING_MODE
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up charging mode selection."""
    async_add_entities([SmartEVChargingModeSelect(entry.runtime_data)])


class SmartEVChargingModeSelect(SmartEVChargingEntity, SelectEntity):
    """Select the active EV charging strategy."""

    _attr_translation_key = "charging_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = CHARGING_MODES

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "charging_mode")

    @property
    def current_option(self) -> str:
        return self.runtime.charging_mode

    async def async_select_option(self, option: str) -> None:
        if option not in CHARGING_MODES:
            raise ValueError(f"Unsupported charging mode: {option}")
        self.runtime.set_setting(CONF_CHARGING_MODE, option)
