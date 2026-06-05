"""Tests for the Weathercloud setup, coordinator, and sensors."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from weathercloud import WeathercloudError

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.weathercloud.const import CONF_DEVICE_ID, DOMAIN

from .conftest import AIRPORT_ID, AIRPORT_INFO, AIRPORT_VALUES, DEVICE_ID


async def test_setup_and_unload(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """The entry loads, creates sensors, and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    # Title is promoted to the scraped station name.
    assert mock_config_entry.title == "Ginometeo"

    state = hass.states.get("sensor.ginometeo_temperature")
    assert state is not None
    assert state.state == "22.8"

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    # The client session must be released on unload.
    assert mock_client.close.called


async def test_setup_fails_on_api_error(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """A data-fetch failure from both endpoints results in a retry."""
    mock_client.get_device_values.side_effect = WeathercloudError("down")
    mock_client.get_device_info.return_value = {}  # no "values" key
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_station_info_failure_is_non_fatal(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """A station-info scrape failure must not block setup."""
    mock_client.get_station_info.side_effect = WeathercloudError("no name")
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    # Falls back to the device ID for the device/entity name.
    assert hass.states.get(f"sensor.{DEVICE_ID}_temperature") is not None


async def test_absent_sensor_is_disabled_by_default(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """Sensors absent from the first response are disabled by default."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # The sample payload has no solar radiation; the entity is registered but
    # disabled, so it has no state.
    assert hass.states.get("sensor.ginometeo_solar_radiation") is None


async def test_last_update_parses_epoch(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """The diagnostic last-update sensor parses the epoch string."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ginometeo_last_update")
    assert state is not None
    expected = datetime.fromtimestamp(1748358122, tz=timezone.utc).isoformat()
    assert state.state == expected


async def test_missing_value_is_handled(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """Empty/garbage raw values do not crash and read as unknown."""
    payload = {"epoch": "1748358122", "temp": "", "hum": "n/a", "bar": "1013.2"}
    mock_client.get_device_values.return_value = payload
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Present-but-empty keys are enabled but read "unknown".
    temp = hass.states.get("sensor.ginometeo_temperature")
    assert temp is not None
    assert temp.state != STATE_UNAVAILABLE
    assert temp.state == "unknown"

    bar = hass.states.get("sensor.ginometeo_pressure")
    assert bar is not None
    assert bar.state == "1013.2"


async def test_airport_station_fallback(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_airport_config_entry,
) -> None:
    """Airport stations (ICAO codes) load via /device/info fallback."""
    from weathercloud import WeathercloudError

    mock_client.get_device_values.side_effect = WeathercloudError(
        "Expected a JSON object from /device/values/LEPA, got: []"
    )
    mock_client.get_device_info.return_value = dict(AIRPORT_INFO)

    mock_airport_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_airport_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_airport_config_entry.state is ConfigEntryState.LOADED

    # Sensors available in the airport payload are reported.
    temp = hass.states.get(f"sensor.{AIRPORT_ID.lower()}_temperature")
    assert temp is not None
    assert temp.state == AIRPORT_VALUES["temp"]

    bar = hass.states.get(f"sensor.{AIRPORT_ID.lower()}_pressure")
    assert bar is not None
    assert bar.state == AIRPORT_VALUES["bar"]

    # Airports don't send epoch, so last_update is unavailable.
    last_update = hass.states.get(f"sensor.{AIRPORT_ID.lower()}_last_update")
    assert last_update is not None
    assert last_update.state == STATE_UNAVAILABLE
