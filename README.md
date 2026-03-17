# mechatronics3

Simple mobile robot based on Arduino, Python, pyFirmata and scikit-learn.

[![CI](https://github.com/vkopey/mechatronics3/actions/workflows/ci.yml/badge.svg)](https://github.com/vkopey/mechatronics3/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Overview

**mechatronics3** is an educational robotics project that turns an Arduino-based
mobile robot into a programmable platform you can drive manually, steer via a
camera, or let loose with a trained machine-learning classifier — all from a
laptop over a serial connection.

| Feature | Description |
|---|---|
| **Manual control** | Tkinter GUI with keyboard-driven motor/servo commands and a live sensor bar chart |
| **Vision strategy** | Camera-based colour tracking that approaches or retreats from detected objects |
| **ML strategy** | Autonomous cube-pushing powered by a GradientBoosting classifier trained on 3-D ultrasonic scans |
| **REST API** | FastAPI server with motor, servo, sensor, detection, and file-management endpoints |
| **Web dashboard** | Single-page UI served at `/` for controlling the robot from a browser |

## Architecture

```
src/mechatronics3/
├── config.py              # pydantic-settings: serial port, pins, HSV, ML params
├── core/
│   ├── board.py           # RobotBoard — Arduino connection & pin lifecycle
│   ├── motor.py           # MotorController — forward, backward, rotate, …
│   ├── sensor.py          # UltrasonicSensor — ping, scan, scan_3d
│   └── servo.py           # ServoController — horizontal & vertical servos
├── detection/
│   ├── color_detector.py  # ColorDetector — OpenCV HSV centroid detection
│   └── ml_detector.py     # CubeDetector — GradientBoosting classifier
├── strategies/
│   ├── manual_strategy.py # Keyboard-driven scan-and-push with tkinter
│   ├── vision_strategy.py # Camera colour-tracking approach/retreat
│   └── ml_strategy.py     # Autonomous ML-based cube-pushing
├── server/
│   ├── app.py             # FastAPI application factory
│   ├── auth.py            # Bearer-token authentication
│   ├── routes/            # REST endpoint modules
│   └── templates/         # Jinja2 web dashboard
├── gui/
│   └── control_panel.py   # Tkinter control panel (used by manual strategy)
└── __main__.py            # CLI entry point
```

## Quick start

```bash
# Clone the repository
git clone https://github.com/vkopey/mechatronics3.git
cd mechatronics3

# Install the core package (editable mode)
pip install -e .

# Or install with optional extras
pip install -e ".[vision]"          # adds OpenCV
pip install -e ".[server]"          # adds FastAPI + Uvicorn
pip install -e ".[dev]"             # adds pytest, ruff, pre-commit
pip install -e ".[dev,vision,server]"  # everything
```

Connect your Arduino, set the serial port, and run:

```bash
# Manual control GUI
mechatronics3 manual

# Vision-based strategy
mechatronics3 vision

# ML autonomous strategy
mechatronics3 ml

# Web server (default http://0.0.0.0:8000)
mechatronics3 server
```

See [docs/getting-started.md](docs/getting-started.md) for detailed
installation and first-run instructions.

## Configuration

All settings are loaded from environment variables (prefix `MECH_`) or a `.env`
file in the project root. Key options:

| Variable | Default | Description |
|---|---|---|
| `MECH_SERIAL_PORT` | `/dev/ttyUSB0` | Arduino serial port |
| `MECH_BAUD_RATE` | `57600` | Serial baud rate |
| `MECH_SERVER_HOST` | `0.0.0.0` | FastAPI bind address |
| `MECH_SERVER_PORT` | `8000` | FastAPI bind port |
| `MECH_AUTH_TOKEN` | `changeme` | Bearer token for API auth |
| `MECH_CAMERA_INDEX` | `0` | OpenCV camera device index |
| `MECH_PINS__ECHO` | `7` | Ultrasonic echo pin |

Nested settings use `__` as a delimiter, e.g. `MECH_PINS__MOTOR_LEFT_FWD=9`.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,vision,server]"

# Lint
ruff check src tests
ruff format --check src tests

# Run tests
pytest

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Documentation

- [Getting started](docs/getting-started.md) — installation, hardware
  requirements, first run
- [Hardware setup](docs/hardware-setup.md) — wiring, pin mapping, supported
  boards
- [API reference](docs/api-reference.md) — REST endpoint documentation
- [Architecture](docs/architecture.md) — internal architecture, module
  descriptions, data flows, configuration reference
- [Changelog](CHANGELOG.md) — migration notes and version history

## Related

- [Pymunk + Nodebox robot competition
  simulation](https://github.com/vkopey/Pymunk_Nodebox_Examples) (examples
  `8_x.py`)

## Demo

[![Simple mobile robot](https://img.youtube.com/vi/v-3aYALHgrE/0.jpg)](https://www.youtube.com/watch?v=v-3aYALHgrE)

## License

This project is licensed under the
[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0).
