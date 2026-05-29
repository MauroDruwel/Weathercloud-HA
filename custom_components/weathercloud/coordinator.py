"""DataUpdateCoordinator for Weathercloud."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from weathercloud import StationInfo, WeathercloudClient, WeathercloudError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type WeathercloudConfigEntry = ConfigEntry[WeathercloudCoordinator]


class WeathercloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls Weathercloud for current conditions."""

    config_entry: WeathercloudConfigEntry
    station_info: StationInfo | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WeathercloudConfigEntry,
        client: WeathercloudClient,
        device_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(
                minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.device_id = device_id

    @property
    def device_name(self) -> str:
        """Return the station name, falling back to the device ID."""
        if self.station_info and self.station_info.name:
            return self.station_info.name
        return self.device_id

    async def _async_setup(self) -> None:
        """Fetch station metadata once, before the first data refresh.

        A scrape failure here is non-fatal: the integration still works, it just
        falls back to the device ID for the station name.
        """
        try:
            self.station_info = await self.hass.async_add_executor_job(
                lambda: self.client.get_station_info(self.device_id, scrape_name=True)
            )
        except WeathercloudError as err:
            _LOGGER.warning(
                "Could not fetch station info for %s, using device ID as name: %s",
                self.device_id,
                err,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch raw current weather values from the API."""
        try:
            return await self.hass.async_add_executor_job(
                self.client.get_device_values, self.device_id
            )
        except WeathercloudError as err:
            raise UpdateFailed(
                f"Error communicating with Weathercloud API: {err}"
            ) from err
