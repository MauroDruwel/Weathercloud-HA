"""DataUpdateCoordinator for Weathercloud."""
from __future__ import annotations

import logging
from datetime import timedelta

from weathercloud import CurrentConditions, StationInfo, WeathercloudClient, WeathercloudError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class WeathercloudCoordinator(DataUpdateCoordinator[CurrentConditions]):
    """Coordinator that polls Weathercloud for current conditions."""

    station_info: StationInfo | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        client: WeathercloudClient,
        device_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.client = client
        self.device_id = device_id

    @property
    def device_name(self) -> str:
        """Return the station name, falling back to the device ID."""
        if self.station_info:
            return self.station_info.name
        return self.device_id

    async def _async_update_data(self) -> CurrentConditions:
        """Fetch current weather conditions from the API."""
        try:
            return await self.hass.async_add_executor_job(
                self.client.get_current_conditions, self.device_id
            )
        except WeathercloudError as err:
            raise UpdateFailed(f"Error communicating with Weathercloud API: {err}") from err
