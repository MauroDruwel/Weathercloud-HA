"""Fixtures for the Weathercloud integration tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from custom_components.weathercloud.const import CONF_DEVICE_ID, DOMAIN

DEVICE_ID = "5726468552"

# A realistic partial /device/values response: values are strings, and a station
# only includes the keys for sensors it actually has (no solarrad/uvi here).
SAMPLE_VALUES = {
    "epoch": "1748358122",
    "temp": "22.8",
    "dew": "15.1",
    "chill": "22.8",
    "heat": "23.0",
    "hum": "62",
    "bar": "1013.2",
    "wspd": "1.2",
    "wspdavg": "0.9",
    "wspdhi": "1.4",
    "wdir": "180",
    "wdiravg": "176",
    "rain": "0.0",
    "rainrate": "0.0",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mock_station_info() -> MagicMock:
    """Return a fake StationInfo object."""
    info = MagicMock()
    info.name = "Ginometeo"
    info.city = "Ingelmunster"
    info.altitude = "18.0"
    return info


@pytest.fixture
def mock_client(mock_station_info: MagicMock) -> Generator[MagicMock]:
    """Patch WeathercloudClient everywhere it is instantiated."""
    client = MagicMock()
    client.get_device_values.return_value = dict(SAMPLE_VALUES)
    client.get_station_info.return_value = mock_station_info
    client.close.return_value = None

    with (
        patch(
            "custom_components.weathercloud.WeathercloudClient",
            return_value=client,
        ),
        patch(
            "custom_components.weathercloud.config_flow.WeathercloudClient",
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
        unique_id=DEVICE_ID,
    )
