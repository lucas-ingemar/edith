# Edith

A minimal display app for Raspberry Pi that combines photos, time, temperature, and public transport in a single calm interface.

Designed for the official 7" Raspberry Pi touchscreen.

---

## Features

* Random photo background
* Clock and date
* Temperature via Home Assistant
* Tram departures via Västtrafik
* Optional screensaver mode (exit on touch)
* Long-running dashboard mode

---

## Requirements

* Raspberry Pi
* Official 7" touchscreen (Gen 1)
* Python 3.11+
* `uv`

---

## Installation

```bash
git clone https://github.com/yourusername/edith.git
cd edith
uv sync
```

---

## Configuration

Provide configuration via environment variables or a config file.

Required values:

* `HOME_ASSISTANT_URL`
* `HOME_ASSISTANT_TOKEN`
* `TEMPERATURE_ENTITY_ID`
* `VASTTRAFIK_CLIENT_ID`
* `VASTTRAFIK_CLIENT_SECRET`
* `VASTTRAFIK_STOP_ID`
* `PHOTO_PATH`

---

## Usage

Run:

```bash
uv run python main.py
```

Screensaver mode:

```bash
uv run python main.py --screensaver
```

Dashboard mode:

```bash
uv run python main.py --dashboard
```

---

## Integrations

**Home Assistant**
Used for fetching temperature data.

**Västtrafik**
Used for real-time tram departures in Gothenburg.

---

## License

AGPL-3.0
