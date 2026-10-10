"""Smart EV Charging integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import SmartEVChargingRuntime

type SmartEVChargingConfigEntry = ConfigEntry[SmartEVChargingRuntime]


async def _async_config_entry_updated(
    hass: HomeAssistant, entry: SmartEVChargingConfigEntry
) -> None:
    """Reload when externally tracked source entities change."""
    runtime = entry.runtime_data
    if runtime.configured_external_entity_ids != runtime.tracked_external_entity_ids:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartEVChargingConfigEntry
) -> bool:
    """Set up Smart EV Charging from a config entry."""
    runtime = SmartEVChargingRuntime(hass, entry)
    entry.runtime_data = runtime

    entry.async_on_unload(
        entry.add_update_listener(_async_config_entry_updated)
    )

    await runtime.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SmartEVChargingConfigEntry
) -> bool:
    """Unload a Smart EV Charging config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
