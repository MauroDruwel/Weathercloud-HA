"""The Weathercloud integration."""
from __future__ import annotations

from weathercloud import WeathercloudClient

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID
from .coordinator import WeathercloudConfigEntry, WeathercloudCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: WeathercloudConfigEntry) -> bool:
    """Set up Weathercloud from a config entry."""
    device_id: str = entry.data[CONF_DEVICE_ID]

    client = WeathercloudClient()
    # Register cleanup immediately so the connection pool is released even if
    # setup fails before the entry is fully loaded.
    entry.async_on_unload(client.close)

    coordinator = WeathercloudCoordinator(hass, entry, client, device_id)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Promote the scraped station name to the entry title once we have it.
    info = coordinator.station_info
    if info and info.name and info.name != device_id and entry.title != info.name:
        hass.config_entries.async_update_entry(entry, title=info.name)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when the user changes options (e.g. poll interval).
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def _async_reload_on_update(
    hass: HomeAssistant, entry: WeathercloudConfigEntry
) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: WeathercloudConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
