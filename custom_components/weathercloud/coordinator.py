"""DataUpdateCoordinator for Weathercloud."""

from __future__ import annotations

import contextlib
import inspect
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from weathercloud import AsyncWeathercloudClient
from weathercloud.core.api_error import ApiError
from weathercloud.core.parse_error import ParsingError

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type WeathercloudConfigEntry = ConfigEntry[WeathercloudCoordinator]


@dataclass
class StationMetadata:
    """Metadata describing a Weathercloud weather station."""

    device_id: str
    name: str | None = None
    city: str | None = None
    altitude: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class WeathercloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls Weathercloud for current conditions."""

    config_entry: WeathercloudConfigEntry
    station_info: StationMetadata | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WeathercloudConfigEntry,
        client: AsyncWeathercloudClient,
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
            city: str | None = None
            altitude: str | None = None
            try:
                res = self.client.device_live.get_info(device_id=self.device_id)
                info = await res if inspect.isawaitable(res) else res
                device = getattr(info, "device", None)
                if device:
                    city = getattr(device, "city", None)
                    altitude = getattr(device, "altitude", None)
            except (ApiError, ParsingError, httpx.HTTPError) as err:
                _LOGGER.debug(
                    "Could not fetch device info for %s: %s", self.device_id, err
                )

            name: str | None = None
            latitude: float | None = None
            longitude: float | None = None
            try:
                res = self.client.stations.get_station_page(device_id=self.device_id)
                html = await res if inspect.isawaitable(res) else res
                if isinstance(html, str):
                    m_title = re.search(
                        r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
                    )
                    if m_title:
                        name = (
                            re.sub(
                                r"\s*-\s*Weathercloud.*$",
                                "",
                                m_title.group(1),
                                flags=re.IGNORECASE,
                            ).strip()
                            or None
                        )

                    m_lat = re.search(r"(?:var\s+)?latitude\s*[:=]\s*([-\d.]+)", html)
                    m_lon = re.search(r"(?:var\s+)?longitude\s*[:=]\s*([-\d.]+)", html)
                    if m_lat:
                        with contextlib.suppress(ValueError):
                            latitude = float(m_lat.group(1))
                    if m_lon:
                        with contextlib.suppress(ValueError):
                            longitude = float(m_lon.group(1))
            except (ApiError, ParsingError, httpx.HTTPError) as err:
                _LOGGER.debug(
                    "Could not fetch station page for %s: %s", self.device_id, err
                )

            self.station_info = StationMetadata(
                device_id=self.device_id,
                name=name,
                city=city,
                altitude=altitude,
                latitude=latitude,
                longitude=longitude,
            )
        except Exception as err:
            _LOGGER.warning(
                "Could not fetch station info for %s, using device ID as name: %s",
                self.device_id,
                err,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch raw current weather values from the API."""
        try:
            res = self.client.device_live.get_values(device_id=self.device_id)
            values = await res if inspect.isawaitable(res) else res
            if hasattr(values, "model_dump"):
                return values.model_dump(exclude_none=True)
            if isinstance(values, dict):
                return values
            return dict(values)
        except (ApiError, ParsingError, httpx.HTTPError) as err:
            raise UpdateFailed(
                f"Error communicating with Weathercloud API: {err}"
            ) from err
