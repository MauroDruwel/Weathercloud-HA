"""The Weathercloud integration."""

from __future__ import annotations

import inspect
import logging

import httpx
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from weathercloud import AsyncWeathercloudClient

from .const import CONF_DEVICE_ID
from .coordinator import WeathercloudConfigEntry, WeathercloudCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: WeathercloudConfigEntry
) -> bool:
    """Set up Weathercloud from a config entry."""
    device_id: str = entry.data[CONF_DEVICE_ID]
    username: str | None = entry.data.get(CONF_USERNAME)
    password: str | None = entry.data.get(CONF_PASSWORD)

    httpx_client = httpx.AsyncClient()
    client = AsyncWeathercloudClient(
        requested_with="XMLHttpRequest",
        httpx_client=httpx_client,
    )

    async def _async_close() -> None:
        await httpx_client.aclose()
        if hasattr(client, "close"):
            res = client.close()
            if inspect.isawaitable(res):
                await res
        elif hasattr(client, "aclose"):
            res = client.aclose()
            if inspect.isawaitable(res):
                await res

    # Register cleanup immediately so the connection pool is released even if
    # setup fails before the entry is fully loaded.
    entry.async_on_unload(_async_close)

    if username and password:
        try:
            res = client.auth.with_raw_response.login(
                login_form_entity=username,
                login_form_password=password,
            )
            raw = await res if inspect.isawaitable(res) else res
            response_obj = getattr(raw, "_response", raw)
            resp_text = getattr(response_obj, "text", "")
            resp_url = getattr(response_obj, "url", None)
            url_path = getattr(resp_url, "path", "")
            if "invalid" in resp_text.lower() or url_path.endswith("/signin"):
                _LOGGER.warning(
                    "Weathercloud login failed for %s: invalid credentials", username
                )
        except Exception as err:
            _LOGGER.warning("Weathercloud authentication error: %s", err)

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
