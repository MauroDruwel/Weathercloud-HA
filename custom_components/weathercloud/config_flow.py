"""Config flow for Weathercloud."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from weathercloud import WeathercloudClient, WeathercloudError

from homeassistant import data_entry_flow
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import WeathercloudConfigEntry

_LOGGER = logging.getLogger(__name__)

class WeathercloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Weathercloud."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: WeathercloudConfigEntry,
    ) -> WeathercloudOptionsFlow:
        """Return the options flow handler."""
        return WeathercloudOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user enters a station ID."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            advanced = user_input.get("advanced_options") or {}
            username = (advanced.get(CONF_USERNAME) or "").strip() or None
            password = (advanced.get(CONF_PASSWORD) or "").strip() or None

            try:
                await self._validate_device_id(device_id, username, password)
            except WeathercloudError as err:
                if "Login failed" in str(err):
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating station ID %s", device_id)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device_id,
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        # Build schema using the collapsible section helper for advanced/credentials fields
        user_input = user_input or {}
        advanced_input = user_input.get("advanced_options") or {}
        data_schema = vol.Schema({
            vol.Required(
                CONF_DEVICE_ID,
                default=user_input.get(CONF_DEVICE_ID, ""),
            ): str,
            "advanced_options": data_entry_flow.section(
                vol.Schema({
                    vol.Optional(
                        CONF_USERNAME,
                        default=advanced_input.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Optional(
                        CONF_PASSWORD,
                        default=advanced_input.get(CONF_PASSWORD, ""),
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }),
                {"collapsed": True},
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_device_id(
        self,
        device_id: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Validate the station ID by fetching raw values.

        Works for partial stations too — we only require a parseable response
        carrying an ``epoch`` timestamp.
        """
        client = WeathercloudClient(username=username, password=password)
        try:
            data = await self.hass.async_add_executor_job(
                client.get_device_values, device_id
            )
        finally:
            await self.hass.async_add_executor_job(client.close)

        if not isinstance(data, dict) or "epoch" not in data:
            raise WeathercloudError("Unexpected response from station")


class WeathercloudOptionsFlow(OptionsFlow):
    """Options flow to configure the poll interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the poll-interval option."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=1,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
