"""Config flow for Weathercloud."""

from __future__ import annotations

import inspect
import logging
from typing import Any

import httpx
import voluptuous as vol
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

from weathercloud import AsyncWeathercloudClient
from weathercloud.core.api_error import ApiError
from weathercloud.core.parse_error import ParsingError

from .const import (
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_ON_MAP,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOW_ON_MAP,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import WeathercloudConfigEntry

_LOGGER = logging.getLogger(__name__)


class WeathercloudAuthError(Exception):
    """Exception raised when authentication fails."""


class WeathercloudConnectionError(Exception):
    """Exception raised when connecting or fetching station data fails."""


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
            advanced = user_input.get("login_details") or {}
            username = (advanced.get(CONF_USERNAME) or "").strip() or None
            password = (advanced.get(CONF_PASSWORD) or "").strip() or None

            try:
                await self._validate_device_id(device_id, username, password)
            except WeathercloudAuthError:
                errors["base"] = "invalid_auth"
            except (
                WeathercloudConnectionError,
                ApiError,
                ParsingError,
                httpx.HTTPError,
            ):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception(
                    "Unexpected error validating station ID %s", device_id
                )
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
                        CONF_SHOW_ON_MAP: user_input.get(
                            CONF_SHOW_ON_MAP, DEFAULT_SHOW_ON_MAP
                        ),
                    },
                )

        # Build schema using the collapsible section helper for advanced/credentials fields
        user_input = user_input or {}
        advanced_input = user_input.get("login_details") or {}
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_ID,
                    default=user_input.get(CONF_DEVICE_ID, ""),
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT, autocomplete="one-time-code"
                    )
                ),
                vol.Optional(
                    CONF_SHOW_ON_MAP,
                    default=user_input.get(CONF_SHOW_ON_MAP, DEFAULT_SHOW_ON_MAP),
                ): bool,
                "login_details": data_entry_flow.section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_USERNAME,
                                default=advanced_input.get(CONF_USERNAME, ""),
                            ): TextSelector(
                                TextSelectorConfig(
                                    type=TextSelectorType.TEXT,
                                    autocomplete="one-time-code",
                                )
                            ),
                            vol.Optional(
                                CONF_PASSWORD,
                                default=advanced_input.get(CONF_PASSWORD, ""),
                            ): TextSelector(
                                TextSelectorConfig(
                                    type=TextSelectorType.PASSWORD,
                                    autocomplete="new-password",
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )

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
        httpx_client = httpx.AsyncClient()
        client = AsyncWeathercloudClient(
            requested_with="XMLHttpRequest",
            httpx_client=httpx_client,
        )
        try:
            if username and password:
                try:
                    res = client.auth.with_raw_response.login(
                        login_form_entity=username,
                        login_form_password=password,
                    )
                    raw = await res if inspect.isawaitable(res) else res
                    response_obj = getattr(raw, "_response", raw)
                    resp_text = getattr(response_obj, "text", "")
                    resp_url = getattr(response_obj, "url", None)
                    url_path = getattr(resp_url, "path", "")
                    if "invalid" in resp_text.lower() or url_path.endswith("/signin"):
                        raise WeathercloudAuthError("Invalid username or password")
                except (ApiError, httpx.HTTPError) as err:
                    if getattr(err, "status_code", None) in (401, 403):
                        raise WeathercloudAuthError(
                            "Invalid username or password"
                        ) from err
                    raise WeathercloudConnectionError(
                        f"Connection error during login: {err}"
                    ) from err

            try:
                res = client.device_live.get_values(device_id=device_id)
                values = await res if inspect.isawaitable(res) else res
            except (ApiError, ParsingError, httpx.HTTPError) as err:
                raise WeathercloudConnectionError(
                    f"Error fetching station data: {err}"
                ) from err

            if isinstance(values, dict):
                epoch = values.get("epoch")
            else:
                epoch = getattr(values, "epoch", None)

            if epoch is None:
                raise WeathercloudConnectionError("Unexpected response from station")
        finally:
            await httpx_client.aclose()
            if hasattr(client, "close"):
                close_res = client.close()
                if inspect.isawaitable(close_res):
                    await close_res


class WeathercloudOptionsFlow(OptionsFlow):
    """Options flow to configure the poll interval and map display."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_scan = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_show_on_map = self.config_entry.options.get(
            CONF_SHOW_ON_MAP,
            self.config_entry.data.get(CONF_SHOW_ON_MAP, DEFAULT_SHOW_ON_MAP),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current_scan): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(CONF_SHOW_ON_MAP, default=current_show_on_map): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
