# 🌦️ Weathercloud for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/MauroDruwel/Weathercloud-HA/actions/workflows/validate.yml/badge.svg)](https://github.com/MauroDruwel/Weathercloud-HA/actions/workflows/validate.yml)
[![Tests](https://github.com/MauroDruwel/Weathercloud-HA/actions/workflows/tests.yml/badge.svg)](https://github.com/MauroDruwel/Weathercloud-HA/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Pull live readings from any public [Weathercloud](https://app.weathercloud.net)
personal weather station straight into Home Assistant — **no account, no API key,
no cloud login**. Just paste a station ID and you're done.

> ⚠️ Built on the unofficial, reverse-engineered [`weathercloud`](https://pypi.org/project/weathercloud/)
> library. Not affiliated with or endorsed by Weathercloud; upstream endpoints
> may change without notice.

## ✨ Highlights

- 🔌 **Zero config** — no account, no token. A station ID is all it takes.
- 🧠 **Smart sensor detection** — your station's sensors are enabled; the ones it
  doesn't have are hidden away (disabled by default), so your dashboard stays clean.
- 🏠 **One device per station** — every reading lands neatly under a single HA device.
- ⏱️ **Polite polling** — defaults to every 10 min (the free-tier update rate), and
  you can tune it from 1–60 min in the options.
- 🌍 **Stations & airports** — works with personal stations *and* METAR airport IDs.

## 📦 Installation

### Via HACS (custom repository)

1. HACS → **⋮** → **Custom repositories**
2. Add `https://github.com/MauroDruwel/Weathercloud-HA` with category **Integration**
3. Install **Weathercloud**, then **restart** Home Assistant

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MauroDruwel&repository=Weathercloud-HA&category=integration)

### Manual

Copy `custom_components/weathercloud/` into your `config/custom_components/`
directory and restart Home Assistant.

## 🚀 Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for **Weathercloud**
3. Enter your **Station ID** — the number at the end of the station URL:

```
app.weathercloud.net/d5726468552  →  Station ID: 5726468552
```

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=weathercloud)

Add as many stations as you like — repeat the flow for each. To change how often a
station is polled, open its entry and hit **Configure**.

## 🌡️ Sensors

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
| Rain | mm | Daily total (long-term statistics) |
| Rain Rate | mm/h | |
| Solar Radiation | W/m² | |
| UV Index | — | |
| Last Update | timestamp | Diagnostic |

> 💡 Sensors your station doesn't report are **disabled by default**. Want one
> anyway? Flip it on in the entity settings — it'll show *unavailable* if the
> station truly has no data for it.

## 🧯 Troubleshooting

- **"Cannot connect"** — double-check the station ID (digits only, no `d` prefix)
  and make sure the station is public and online.
- **Some sensors missing?** That's by design — your station simply doesn't report
  them. Enable them manually if you expected otherwise.
- **No icon in older Home Assistant?** Local brand icons are served from
  `custom_components/weathercloud/brand/` on **HA 2026.3+**. On older versions the
  integration works perfectly — only the logo is missing. No biggie. 😉

## 🙋 FAQ

- **Do I need a Weathercloud account?** Nope. Everything here is public data.
- **How fresh is the data?** Free stations push roughly every 10 minutes, so polling
  faster won't get you newer numbers — just more requests.
- **METAR airports?** Yes — ICAO-style station IDs work too.

## 🛠️ Development

```sh
git clone https://github.com/MauroDruwel/Weathercloud-HA
cd Weathercloud-HA
python -m venv .venv && source .venv/bin/activate
pip install pytest-homeassistant-custom-component weathercloud
pytest        # run the test suite
```

GitHub Actions run **hassfest**, the **HACS validation**, and the **pytest** suite
on every push and pull request.

## 🔗 Related

- 🐍 Python library: [`weathercloud`](https://github.com/MauroDruwel/weathercloud) ·
  [PyPI](https://pypi.org/project/weathercloud/)

## 📄 License

[MIT](LICENSE)
