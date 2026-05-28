# Weathercloud for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant integration for [Weathercloud](https://app.weathercloud.net) personal weather stations. Sensors are auto-detected based on what your specific station supports — sensors not available on your hardware are disabled by default.

---

## Features

- Automatic sensor detection — only sensors your station reports are enabled
- 16 weather sensors: temperature, humidity, pressure, wind (speed/gust/direction), rain, UV index, solar radiation, dew point, wind chill, heat index, and more
- Polls every 10 minutes (matching the Weathercloud free-tier update rate)
- Each station appears as a single HA device

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/MauroDruwel/Weathercloud-HA` as an **Integration**
3. Install **Weathercloud** and restart Home Assistant

### Manual

Copy the `custom_components/weathercloud/` folder into your HA `config/custom_components/` directory and restart.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Weathercloud**
3. Enter the **Station ID** — the number at the end of the station URL:
   ```
   app.weathercloud.net/d5726468552  →  Station ID: 5726468552
   ```

To add more stations, repeat the process. To remove a station, delete the integration entry.

## Sensors

| Sensor | Unit | Notes |
|---|---|---|
| Temperature | °C | |
| Dew Point | °C | |
| Wind Chill | °C | |
| Heat Index | °C | |
| Humidity | % | |
| Pressure | hPa | |
| Wind Speed | m/s | Instantaneous |
| Wind Speed Average | m/s | |
| Wind Gust | m/s | |
| Wind Direction | ° | Instantaneous |
| Wind Direction Average | ° | |
| Rain | mm | Daily total |
| Rain Rate | mm/h | |
| Solar Radiation | W/m² | |
| UV Index | UV index | |
| Last Update | timestamp | Diagnostic |

Sensors not reported by your station will be **disabled by default** and shown as unavailable. You can manually enable them in the entity settings if needed.

## Notes

- No Weathercloud account is required
- Station IDs work for both personal stations and METAR airport stations
- Based on the unofficial [`weathercloud`](https://pypi.org/project/weathercloud/) Python library

## Brand icon

The current `brand/icon.png` is a placeholder. Replace it with a proper 512×512 PNG before submitting to HACS.
