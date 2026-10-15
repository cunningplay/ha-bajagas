"""BajaGas LP price: scrapes the supplier's per-liter price for a chosen city."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION
from .coordinator import BajaGasConfigEntry, BajaGasCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BajaGasConfigEntry) -> bool:
    """Set up the BajaGas price for one city."""
    coordinator = BajaGasCoordinator(hass, entry)
    if await coordinator.async_load_store():
        # Stored prices are served at once; the page is scraped in the
        # background so HA starts (and the sensor restores) even with no internet.
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), f"{DOMAIN} initial refresh"
        )
    else:
        await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BajaGasConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored prices for a removed city."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
