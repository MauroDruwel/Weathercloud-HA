"""Constants for the Weathercloud integration."""

DOMAIN = "weathercloud"

ATTRIBUTION = "Data provided by Weathercloud"

from homeassistant.const import CONF_SHOW_ON_MAP

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10
DEFAULT_SHOW_ON_MAP: bool = False
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 60

# Values at or below this are treated as "no data" sentinels (e.g. -9999)
SENTINEL_THRESHOLD = -9990
