"""The Weathercloud integration."""
from __future__ import annotations

import logging

from weathercloud import WeathercloudClient, WeathercloudError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import WeathercloudCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weathercloud from a config entry."""
    device_id: str = entry.data[CONF_DEVICE_ID]
    client = WeathercloudClient()

    coordinator = WeathercloudCoordinator(hass, client, device_id)

    # Fetch station info best-effort — a scrape failure must not block setup.
    try:
        station_info = await hass.async_add_executor_job(
            lambda: client.get_station_info(device_id, scrape_name=True)
        )
        coordinator.station_info = station_info

        # Update the config entry title once we have the real station name.
        if station_info.name and station_info.name != device_id:
            hass.config_entries.async_update_entry(entry, title=station_info.name)
    except WeathercloudError:
        _LOGGER.warning(
            "Could not fetch station info for %s — using device ID as name", device_id
        )

    # This fetches live data; raises ConfigEntryNotReady on failure.
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Failed to fetch initial data for {device_id}: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
