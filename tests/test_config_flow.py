"""Tests for the Weathercloud config and options flow."""
from __future__ import annotations

from unittest.mock import MagicMock

from weathercloud import WeathercloudError

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.weathercloud.const import (
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from .conftest import DEVICE_ID


async def test_user_flow_success(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """A valid station ID creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: f"  {DEVICE_ID}  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_USERNAME: None,
        CONF_PASSWORD: None,
    }
    # The validation client must be closed regardless of outcome.
    assert mock_client.close.called


async def test_user_flow_with_credentials_success(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """A valid station ID and valid credentials creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_USERNAME: "testuser",
            CONF_PASSWORD: "testpassword",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_USERNAME: "testuser",
        CONF_PASSWORD: "testpassword",
    }
    assert mock_client.close.called


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """A WeathercloudError surfaces as a cannot_connect error."""
    mock_client.get_device_values.side_effect = WeathercloudError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert mock_client.close.called


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """A login-related WeathercloudError surfaces as an invalid_auth error."""
    mock_client.get_device_values.side_effect = WeathercloudError("Login failed: invalid password")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_USERNAME: "baduser",
            CONF_PASSWORD: "badpassword",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert mock_client.close.called


async def test_user_flow_bad_response(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """A response without an epoch is rejected."""
    mock_client.get_device_values.return_value = {"foo": "bar"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_duplicate(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """The same station cannot be added twice."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: DEVICE_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry
) -> None:
    """The options flow stores a new poll interval."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 15}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 15
