"""Fixtures for the Weathercloud integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weathercloud import DeviceInfo, DeviceInfoDevice, DeviceValues

from custom_components.weathercloud.const import (
    CONF_DEVICE_ID,
    CONF_SHOW_ON_MAP,
    DOMAIN,
)

DEVICE_ID = "5726468552"

# A realistic partial /device/values response: values are strings or numbers,
# and a station only includes the keys for sensors it actually has (no solarrad/uvi here).
SAMPLE_VALUES = {
    "epoch": 1748358122,
    "temp": 22.8,
    "dew": 15.1,
    "chill": 22.8,
    "heat": 23.0,
    "hum": 62,
    "bar": 1013.2,
    "wspd": 1.2,
    "wspdavg": 0.9,
    "wspdhi": 1.4,
    "wdir": 180,
    "wdiravg": 176,
    "rain": 0.0,
    "rainrate": 0.0,
    "tempin": 21.5,
    "humin": 55,
    "heatin": 22.0,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mock_station_info() -> MagicMock:
    """Return a fake StationInfo-like object."""
    info = MagicMock()
    info.name = "Ginometeo"
    info.city = "Ingelmunster"
    info.altitude = "18.0"
    info.latitude = 50.8303
    info.longitude = 3.2697
    return info


@pytest.fixture
def mock_client(mock_station_info: MagicMock) -> Generator[MagicMock]:
    """Patch AsyncWeathercloudClient everywhere it is instantiated."""
    client = MagicMock()

    client.device_live = MagicMock()
    client.device_live.get_values = AsyncMock(
        return_value=DeviceValues(**SAMPLE_VALUES)
    )

    async def _mock_get_info(device_id: str):
        return DeviceInfo(
            device=DeviceInfoDevice(
                city=mock_station_info.city,
                altitude=mock_station_info.altitude,
            )
        )

    client.device_live.get_info = AsyncMock(side_effect=_mock_get_info)

    client.stations = MagicMock()

    async def _mock_get_station_page(device_id: str):
        lat_part = (
            f"var latitude = {mock_station_info.latitude};"
            if mock_station_info.latitude is not None
            else ""
        )
        lon_part = (
            f"var longitude = {mock_station_info.longitude};"
            if mock_station_info.longitude is not None
            else ""
        )
        return (
            f"<title>{mock_station_info.name} - Weathercloud | Global network of weather stations</title>"
            f"<script>{lat_part} {lon_part}</script>"
        )

    client.stations.get_station_page = AsyncMock(side_effect=_mock_get_station_page)

    client.auth = MagicMock()
    mock_raw_login = MagicMock()
    mock_raw_login._response.text = "Redirecting"
    mock_raw_login._response.url.path = "/"
    client.auth.with_raw_response = MagicMock()
    client.auth.with_raw_response.login = AsyncMock(return_value=mock_raw_login)
    client.auth.login = AsyncMock(return_value=None)
    client.close = MagicMock(return_value=None)

    with (
        patch(
            "custom_components.weathercloud.AsyncWeathercloudClient",
            return_value=client,
        ),
        patch(
            "custom_components.weathercloud.config_flow.AsyncWeathercloudClient",
            return_value=client,
        ),
    ):
        yield client


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry for the Weathercloud integration."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    return MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_ID,
        data={CONF_DEVICE_ID: DEVICE_ID},
        options={CONF_SHOW_ON_MAP: True},
        unique_id=DEVICE_ID,
    )
