"""Config flow for Weathercloud."""
from __future__ import annotations

import voluptuous as vol
from weathercloud import WeathercloudClient, WeathercloudError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_DEVICE_ID, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID): str,
})


class WeathercloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Weathercloud."""

    VERSION = 1

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
        """Validate the device ID by fetching live conditions."""
        client = WeathercloudClient()
        await self.hass.async_add_executor_job(
            client.get_current_conditions, device_id
        )
