"""Date/time entities for Smart EV Charging."""

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SmartEVChargingConfigEntry
from .const import CONF_DEPARTURE
from .coordinator import SmartEVChargingRuntime
from .entity import SmartEVChargingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartEVChargingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up departure date/time."""
    async_add_entities([SmartEVDepartureDateTime(entry.runtime_data)])


class SmartEVDepartureDateTime(SmartEVChargingEntity, DateTimeEntity):
    """Requested departure date and time."""

    _attr_translation_key = "departure"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: SmartEVChargingRuntime) -> None:
        super().__init__(runtime, "departure")

    @property
    def native_value(self) -> datetime | None:
        return self.runtime.departure

    async def async_set_value(self, value: datetime) -> None:
        self.runtime.set_setting(CONF_DEPARTURE, value)
