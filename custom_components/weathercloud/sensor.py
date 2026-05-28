"""Sensor platform for the Weathercloud integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from weathercloud import CurrentConditions

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
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

from .const import DOMAIN, SENTINEL_THRESHOLD
from .coordinator import WeathercloudCoordinator


@dataclass(frozen=True, kw_only=True)
class WeathercloudSensorEntityDescription(SensorEntityDescription):
    """Describes a Weathercloud sensor entity."""

    value_fn: Callable[[CurrentConditions], float | int | datetime | None]


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
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.temperature,
    ),
    WeathercloudSensorEntityDescription(
        key="dew_point",
        translation_key="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.dew_point,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_chill",
        translation_key="wind_chill",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.wind_chill,
    ),
    WeathercloudSensorEntityDescription(
        key="heat_index",
        translation_key="heat_index",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.heat_index,
    ),
    WeathercloudSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda c: c.humidity,
    ),
    WeathercloudSensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.pressure,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.wind_speed,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_speed_avg",
        translation_key="wind_speed_avg",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.wind_speed_avg,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_gust",
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.wind_gust,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_direction",
        translation_key="wind_direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass",
        value_fn=lambda c: c.wind_direction,
    ),
    WeathercloudSensorEntityDescription(
        key="wind_direction_avg",
        translation_key="wind_direction_avg",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:compass",
        value_fn=lambda c: c.wind_direction_avg,
    ),
    WeathercloudSensorEntityDescription(
        key="rain",
        translation_key="rain",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda c: c.rain,
    ),
    WeathercloudSensorEntityDescription(
        key="rain_rate",
        translation_key="rain_rate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.rain_rate,
    ),
    WeathercloudSensorEntityDescription(
        key="solar_radiation",
        translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda c: c.solar_radiation,
    ),
    WeathercloudSensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        native_unit_of_measurement=UV_INDEX,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sun-wireless",
        suggested_display_precision=0,
        value_fn=lambda c: c.uv_index,
    ),
    WeathercloudSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: datetime.fromtimestamp(c.epoch, tz=timezone.utc),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weathercloud sensors from a config entry."""
    coordinator: WeathercloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WeathercloudSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class WeathercloudSensorEntity(CoordinatorEntity[WeathercloudCoordinator], SensorEntity):
    """A single Weathercloud sensor entity."""

    _attr_has_entity_name = True
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

        # Disable by default sensors whose first reading is a no-data sentinel.
        # The user can manually enable them later if a sensor is added to the station.
        if coordinator.data is not None and description.key != "last_update":
            initial = description.value_fn(coordinator.data)
            if not _is_valid(initial):
                self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | int | datetime | None:
        """Return the sensor value, or None when the reading is a no-data sentinel."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)
        # datetime values (last_update) are always valid
        if isinstance(value, datetime):
            return value
        return value if _is_valid(value) else None


def _station_extra_info(coordinator: WeathercloudCoordinator) -> dict:
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
