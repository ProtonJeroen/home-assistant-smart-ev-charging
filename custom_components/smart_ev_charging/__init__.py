"""Smart EV Charging integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import SmartEVChargingRuntime

type SmartEVChargingConfigEntry = ConfigEntry[SmartEVChargingRuntime]


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartEVChargingConfigEntry
) -> bool:
    """Set up Smart EV Charging from a config entry."""
    runtime = SmartEVChargingRuntime(hass, entry)
    entry.runtime_data = runtime

    await runtime.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SmartEVChargingConfigEntry
) -> bool:
    """Unload a Smart EV Charging config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
