"""Base entities for Smart EV Charging."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import SmartEVChargingRuntime


class SmartEVChargingEntity(Entity):
    """Base entity for one configured vehicle."""

    _attr_has_entity_name = True

    def __init__(self, runtime: SmartEVChargingRuntime, key: str) -> None:
        self.runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Smart EV Charging",
            model="EV charging planner",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.runtime.async_add_listener(self.async_write_ha_state)
        )
