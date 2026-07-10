"""Sensor platform for the Weathercloud integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UV_INDEX,
    EntityCategory,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, SENTINEL_THRESHOLD
from .coordinator import WeathercloudConfigEntry, WeathercloudCoordinator

# Sensors only read shared coordinator data; no per-entity I/O is performed.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WeathercloudSensorEntityDescription(SensorEntityDescription):
    """Describes a Weathercloud sensor entity."""

    # Raw API key in the /device/values response dict.
    api_key: str
    value_fn: Callable[[dict[str, Any]], float | int | datetime | None]


def _float(data: dict[str, Any], key: str) -> float | None:
    """Coerce a raw (string) API value to float, returning None if invalid."""
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(data: dict[str, Any], key: str) -> int | None:
    """Coerce a raw (string) API value to int, returning None if invalid."""
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _timestamp(data: dict[str, Any]) -> datetime | None:
    """Parse the epoch field (a unix timestamp string) into a datetime."""
    value = data.get("epoch")
    if value is None or value == "":
        return None
    try:
        return datetime.fromtimestamp(int(float(value)), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _is_valid(value: float | int | None) -> bool:
    """Return True if the value is real sensor data, not a no-data sentinel."""
    if value is None:
        return False
    if isinstance(value, (int, float)) and value <= SENTINEL_THRESHOLD:
        return False
    return True


SENSOR_DESCRIPTIONS: tuple[WeathercloudSensorEntityDescription, ...] = (
    WeathercloudSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        api_key="temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "temp"),
    ),
    WeathercloudSensorEntityDescription(
        key="dew_point",
        translation_key="dew_point",
        api_key="dew",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "dew"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_chill",
        translation_key="wind_chill",
        api_key="chill",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "chill"),
    ),
    WeathercloudSensorEntityDescription(
        key="heat_index",
        translation_key="heat_index",
        api_key="heat",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "heat"),
    ),
    WeathercloudSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        api_key="hum",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: _int(d, "hum"),
    ),
    WeathercloudSensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        api_key="bar",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "bar"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_speed",
        translation_key="wind_speed",
        api_key="wspd",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "wspd"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_speed_avg",
        translation_key="wind_speed_avg",
        api_key="wspdavg",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "wspdavg"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_gust",
        translation_key="wind_gust",
        api_key="wspdhi",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "wspdhi"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_direction",
        translation_key="wind_direction",
        api_key="wdir",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass",
        value_fn=lambda d: _int(d, "wdir"),
    ),
    WeathercloudSensorEntityDescription(
        key="wind_direction_avg",
        translation_key="wind_direction_avg",
        api_key="wdiravg",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass",
        value_fn=lambda d: _int(d, "wdiravg"),
    ),
    WeathercloudSensorEntityDescription(
        key="rain",
        translation_key="rain",
        api_key="rain",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "rain"),
    ),
    WeathercloudSensorEntityDescription(
        key="rain_rate",
        translation_key="rain_rate",
        api_key="rainrate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "rainrate"),
    ),
    WeathercloudSensorEntityDescription(
        key="solar_radiation",
        translation_key="solar_radiation",
        api_key="solarrad",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "solarrad"),
    ),
    WeathercloudSensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        api_key="uvi",
        native_unit_of_measurement=UV_INDEX,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sun-wireless",
        suggested_display_precision=0,
        value_fn=lambda d: _int(d, "uvi"),
    ),
    WeathercloudSensorEntityDescription(
        key="inside_temperature",
        translation_key="inside_temperature",
        api_key="tempin",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "tempin"),
    ),
    WeathercloudSensorEntityDescription(
        key="inside_humidity",
        translation_key="inside_humidity",
        api_key="humin",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: _int(d, "humin"),
    ),
    WeathercloudSensorEntityDescription(
        key="inside_heat_index",
        translation_key="inside_heat_index",
        api_key="heatin",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _float(d, "heatin"),
    ),
    WeathercloudSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        api_key="epoch",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_timestamp,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeathercloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weathercloud sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        WeathercloudSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class WeathercloudSensorEntity(CoordinatorEntity[WeathercloudCoordinator], SensorEntity):
    """A single Weathercloud sensor entity."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: WeathercloudSensorEntityDescription

    def __init__(
        self,
        coordinator: WeathercloudCoordinator,
        description: WeathercloudSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name=coordinator.device_name,
            manufacturer="Weathercloud",
            configuration_url=f"https://app.weathercloud.net/d{coordinator.device_id}",
            **_station_extra_info(coordinator),
        )

        # Disable sensors whose API key was absent in the first response, so the
        # device only surfaces sensors the station actually reports.
        if (
            coordinator.data is not None
            and description.key != "last_update"
            and description.api_key not in coordinator.data
        ):
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | int | datetime | None:
        """Return the sensor value, or None when the key is absent or sentinel."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)
        if isinstance(value, datetime):
            return value
        return value if _is_valid(value) else None


def _station_extra_info(coordinator: WeathercloudCoordinator) -> dict[str, str]:
    """Build optional DeviceInfo fields from station metadata."""
    info = coordinator.station_info
    if info is None:
        return {}
    parts: list[str] = []
    if info.city:
        parts.append(info.city)
    if info.altitude:
        parts.append(f"alt. {info.altitude} m")
    return {"model": ", ".join(parts)} if parts else {}
