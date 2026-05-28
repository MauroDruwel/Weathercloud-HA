"""Constants for the Weathercloud integration."""

DOMAIN = "weathercloud"

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 60

# Values at or below this are treated as "no data" sentinels (e.g. -9999)
SENTINEL_THRESHOLD = -9990
