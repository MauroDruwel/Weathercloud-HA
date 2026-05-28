"""Config flow for Weathercloud."""
from __future__ import annotations

import voluptuous as vol
from weathercloud import WeathercloudClient, WeathercloudError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID): str,
})


class WeathercloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Weathercloud."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WeathercloudOptionsFlow()

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            try:
                await self._validate_device_id(device_id)
            except WeathercloudError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER = __import__("logging").getLogger(__name__)
                _LOGGER.exception("Unexpected error validating device ID %s", device_id)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device_id,
                    data={CONF_DEVICE_ID: device_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _validate_device_id(self, device_id: str) -> None:
        """Validate the device ID by fetching raw values — works for partial stations too."""
        client = WeathercloudClient()
        data = await self.hass.async_add_executor_job(
            client.get_device_values, device_id
        )
        if not isinstance(data, dict) or "epoch" not in data:
            raise WeathercloudError("Unexpected response from station")


class WeathercloudOptionsFlow(OptionsFlow):
    """Options flow to configure poll interval."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
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
