"""Weather platform for the Weathercloud integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, SENTINEL_THRESHOLD
from .coordinator import WeathercloudConfigEntry, WeathercloudCoordinator

# The weather entity only reads shared coordinator data; no per-entity I/O.
PARALLEL_UPDATES = 0

# Map WMO weather interpretation codes (as returned by /forecast/daily) to
# Home Assistant weather conditions.
_WMO_CONDITION_MAP: dict[int, str] = {
    0: ATTR_CONDITION_SUNNY,
    1: ATTR_CONDITION_SUNNY,
    2: ATTR_CONDITION_PARTLYCLOUDY,
    3: ATTR_CONDITION_CLOUDY,
    45: ATTR_CONDITION_FOG,
    48: ATTR_CONDITION_FOG,
    51: ATTR_CONDITION_RAINY,
    53: ATTR_CONDITION_RAINY,
    55: ATTR_CONDITION_RAINY,
    56: ATTR_CONDITION_SNOWY_RAINY,
    57: ATTR_CONDITION_SNOWY_RAINY,
    61: ATTR_CONDITION_RAINY,
    63: ATTR_CONDITION_RAINY,
    65: ATTR_CONDITION_POURING,
    66: ATTR_CONDITION_SNOWY_RAINY,
    67: ATTR_CONDITION_SNOWY_RAINY,
    71: ATTR_CONDITION_SNOWY,
    73: ATTR_CONDITION_SNOWY,
    75: ATTR_CONDITION_SNOWY,
    77: ATTR_CONDITION_SNOWY,
    80: ATTR_CONDITION_RAINY,
    81: ATTR_CONDITION_RAINY,
    82: ATTR_CONDITION_POURING,
    85: ATTR_CONDITION_SNOWY,
    86: ATTR_CONDITION_SNOWY,
    95: ATTR_CONDITION_LIGHTNING_RAINY,
    96: ATTR_CONDITION_HAIL,
    99: ATTR_CONDITION_HAIL,
}
# Codes that only make sense as a fallback bucket.
_WMO_FALLBACKS: tuple[tuple[range, str], ...] = (
    (range(4, 20), ATTR_CONDITION_CLOUDY),  # haze/mist/visibility phenomena
    (range(20, 30), ATTR_CONDITION_RAINY),  # recent precipitation
    (range(30, 40), ATTR_CONDITION_EXCEPTIONAL),  # dust/sand storms
    (range(40, 50), ATTR_CONDITION_FOG),
    (range(50, 60), ATTR_CONDITION_RAINY),
    (range(60, 70), ATTR_CONDITION_RAINY),
    (range(70, 80), ATTR_CONDITION_SNOWY),
    (range(80, 90), ATTR_CONDITION_RAINY),
    (range(90, 100), ATTR_CONDITION_LIGHTNING),
)


def _wmo_to_condition(code: int | None) -> str | None:
    """Translate a WMO weather code to a Home Assistant condition string."""
    if code is None:
        return None
    if code in _WMO_CONDITION_MAP:
        return _WMO_CONDITION_MAP[code]
    for bucket, condition in _WMO_FALLBACKS:
        if code in bucket:
            return condition
    return None


def _float(data: dict[str, Any] | None, key: str) -> float | None:
    """Coerce a raw API value to float, filtering no-data sentinels."""
    if data is None:
        return None
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result <= SENTINEL_THRESHOLD:
        return None
    return result


def _int(data: dict[str, Any] | None, key: str) -> int | None:
    """Coerce a raw API value to int, filtering no-data sentinels."""
    result = _float(data, key)
    return None if result is None else int(result)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeathercloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Weathercloud weather entity from a config entry."""
    async_add_entities([WeathercloudWeatherEntity(entry.runtime_data)])


class WeathercloudWeatherEntity(
    CoordinatorEntity[WeathercloudCoordinator], WeatherEntity
):
    """Weather entity backed by live station data plus the WMO daily forecast."""

    _attr_has_entity_name = True
    # Main feature of the device: the entity is named after the station itself,
    # producing an entity ID like weather.<station_name>.
    _attr_name = None
    _attr_attribution = ATTRIBUTION
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS

    def __init__(self, coordinator: WeathercloudCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_weather"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
        )

    # ------------------------------------------------------------------
    # Current conditions (from /device/values via the coordinator)
    # ------------------------------------------------------------------

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        return _float(self.coordinator.data, "temp")

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return the apparent temperature (heat index, then wind chill)."""
        heat = _float(self.coordinator.data, "heat")
        if heat is not None:
            return heat
        return _float(self.coordinator.data, "chill")

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point."""
        return _float(self.coordinator.data, "dew")

    @property
    def humidity(self) -> float | None:
        """Return the relative humidity."""
        return _float(self.coordinator.data, "hum")

    @property
    def native_pressure(self) -> float | None:
        """Return the barometric pressure."""
        return _float(self.coordinator.data, "bar")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        return _float(self.coordinator.data, "wspd")

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return the wind gust speed."""
        return _float(self.coordinator.data, "wspdhi")

    @property
    def wind_bearing(self) -> int | None:
        """Return the wind bearing in degrees."""
        return _int(self.coordinator.data, "wdir")

    @property
    def uv_index(self) -> float | None:
        """Return the UV index."""
        return _float(self.coordinator.data, "uvi")

    @property
    def condition(self) -> str | None:
        """Return the current condition.

        The station itself has no condition sensor, so this is derived from the
        live rain rate when it is raining, otherwise from today's forecast code.
        """
        rain_rate = _float(self.coordinator.data, "rainrate")
        if rain_rate is not None and rain_rate > 0:
            return (
                ATTR_CONDITION_POURING if rain_rate >= 8 else ATTR_CONDITION_RAINY
            )
        today = self._forecast_days()
        if today:
            return _wmo_to_condition(today[0][1])
        return None

    # ------------------------------------------------------------------
    # Forecast (from WeathercloudClient.get_forecast(device_id))
    # ------------------------------------------------------------------

    def _forecast_days(self) -> list[tuple[str, int | None, int | None, int | None]]:
        """Return sorted (date, code, temp_max, temp_min) tuples from the raw dict."""
        raw = self.coordinator.forecast_data
        if not raw:
            return []
        days = raw.get("forecast")
        if not isinstance(days, dict):
            return []
        result: list[tuple[str, int | None, int | None, int | None]] = []
        for date in sorted(days):
            entry = days.get(date)
            if not isinstance(entry, dict):
                continue
            weather = entry.get("weather")
            temperature = entry.get("temperature")
            code = _int(weather if isinstance(weather, dict) else None, "code")
            t_max = _int(
                temperature if isinstance(temperature, dict) else None, "max"
            )
            t_min = _int(
                temperature if isinstance(temperature, dict) else None, "min"
            )
            result.append((date, code, t_max, t_min))
        return result

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        days = self._forecast_days()
        if not days:
            return None
        return [
            Forecast(
                datetime=date,
                condition=_wmo_to_condition(code),
                native_temperature=t_max,
                native_templow=t_min,
            )
            for date, code, t_max, t_min in days
        ]
