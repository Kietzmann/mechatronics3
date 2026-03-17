# Architecture

This document describes the internal architecture of mechatronics3 after its
modernisation from flat Python 2 scripts to a structured Python 3.14 package.

## High-level overview

mechatronics3 is structured as a layered package where higher-level modules
depend on lower-level ones, but never the other way around.

```
                    ┌──────────────┐
                    │   __main__   │  CLI entry point
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  strategies  │ │   server    │ │     gui     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           ▼               ▼               │
    ┌─────────────┐ ┌─────────────┐        │
    │  detection   │ │   routes    │        │
    └──────┬──────┘ └──────┬──────┘        │
           │               │               │
           └───────┬───────┘               │
                   ▼                       │
            ┌─────────────┐                │
            │    core      │◄──────────────┘
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │   config     │
            └─────────────┘
```

## Package layout

```
src/mechatronics3/
├── __init__.py              # Package metadata (__version__)
├── __main__.py              # CLI: argparse dispatcher → server | ml | vision | manual
├── config.py                # pydantic-settings: all hardware and network config
├── core/
│   ├── __init__.py          # Public API re-exports
│   ├── board.py             # RobotBoard — Arduino connection, pin cache, context manager
│   ├── motor.py             # MotorController — left/right motor primitives + compound moves
│   ├── sensor.py            # UltrasonicSensor — ping, 2D scan, 3D scan (dataclasses for results)
│   └── servo.py             # ServoController — horizontal/vertical servo read/write
├── detection/
│   ├── __init__.py          # Public API re-exports
│   ├── ml_detector.py       # CubeDetector — GradientBoosting classifier wrapper
│   └── color_detector.py    # ColorDetector — OpenCV HSV centroid detection, camera lifecycle
├── strategies/
│   ├── __init__.py
│   ├── ml_strategy.py       # Autonomous ML-based cube-pushing loop
│   ├── vision_strategy.py   # Camera-tracking approach/retreat loop
│   └── manual_strategy.py   # Tkinter GUI + keyboard-driven scan-and-push
├── server/
│   ├── __init__.py
│   ├── app.py               # FastAPI application factory + lifespan (hardware init/teardown)
│   ├── auth.py              # Bearer-token authentication dependency
│   ├── routes/
│   │   ├── __init__.py      # Router re-exports
│   │   ├── robot.py         # /api/robot/* — motor, servo, sensor endpoints
│   │   ├── detection.py     # /api/detection/* — colour and ML detection endpoints
│   │   └── files.py         # /api/files/* — upload, execute, delete scripts
│   └── templates/
│       └── index.html       # Single-page web dashboard
└── gui/
    ├── __init__.py
    └── control_panel.py     # Tkinter window: buttons, bar chart, keyboard dispatch
```

## Module details

### `config.py`

Central configuration backed by `pydantic-settings`. All values can be
overridden via `MECH_`-prefixed environment variables or a `.env` file.

| Model | Purpose |
|---|---|
| `PinMap` | Arduino digital pin assignments (motors, servos, echo) |
| `HSVRange` | HSV colour-detection thresholds |
| `ScanConfig` | Ultrasonic scan sweep parameters |
| `MLConfig` | GradientBoosting hyper-parameters |
| `Settings` | Top-level settings aggregating all of the above + serial port, server host, auth token, etc. |

The `get_settings()` function returns a cached singleton. Tests call
`get_settings.cache_clear()` to reset between cases.

### `core/board.py` — `RobotBoard`

Wraps `pyfirmata.Arduino` with:

- Automatic iterator startup and analog reporting
- Pin caching (`digital_output()`, `servo_pin()`) so the same pin spec is
  never requested twice
- `setup_pins(PinMap)` to pre-acquire all pins at once
- Context manager protocol for safe shutdown

### `core/motor.py` — `MotorController`

Drives two DC motors through four digital output pins (left fwd/bwd, right
fwd/bwd). Provides:

- **Primitives**: `right_forward()`, `right_backward()`, `left_forward()`,
  `left_backward()`, `stop()` — each takes a duration and an `auto_stop` flag
- **Compound movements**: `forward()`, `backward()` (both motors with a
  right-side lead-in to compensate for torque asymmetry), `rotate()` (in-place
  turn computed from angle and empirical coefficient)

### `core/sensor.py` — `UltrasonicSensor`

Reads distance via an echo pin and sweeps servos for spatial scanning.

- `ping(samples)` — averaged distance measurement
- `scan()` — horizontal sweep returning `ScanResult(angles, distances)`
- `scan_3d()` — two-axis sweep returning `Scan3DResult(horizontal, vertical,
  detections)` where detections is a binary vector suitable for the ML classifier

### `core/servo.py` — `ServoController`

Thin wrapper around horizontal and vertical servo pins with `write_*()`,
`read_*()`, and `center()`.

### `detection/ml_detector.py` — `CubeDetector`

Wraps `sklearn.ensemble.GradientBoostingClassifier`:

- `fit(x, y)` — trains the model, returns `TrainResult` with accuracy and
  cross-validation scores
- `predict(detections)` / `predict_from_scan(Scan3DResult)` — returns `True`
  if the binary detection vector indicates an object
- `from_config(MLConfig)` factory for constructing from settings

### `detection/color_detector.py` — `ColorDetector`

OpenCV camera-based colour detection:

- Context manager for camera lifecycle (`open()` / `close()`)
- `read_frame()` — capture a BGR + HSV frame pair
- `detect_color()` (static) — HSV inRange + moments → `ColorMatch(x, y, mask)`
  or `None`
- `detect()` — single-range convenience (capture + detect)
- `detect_multi()` — multiple HSV ranges on one captured frame

### `strategies/ml_strategy.py`

Ported from the original `ArduinoRoboCar.py`. Contains pre-recorded training
data as numpy arrays. Main loop:

1. Train `CubeDetector` on startup
2. `scan_3d()` → `predict_from_scan()` → `forward(5)` if detected, else random
   move
3. Runs until `KeyboardInterrupt`

### `strategies/vision_strategy.py`

Ported from `ArduinoRoboCar2.py`. Fetches colour-blob coordinates from a remote
vision server (the FastAPI colour detection endpoint). Compares apparent distance
between two tracked blobs before and after a forward move; retreats if the
target appears larger.

**Bug fix**: the original called `R(1)` which was never defined — replaced with
`motor.backward(1)`.

### `strategies/manual_strategy.py`

Ported from `ArduinoRoboCar3.py`. Opens a Tkinter GUI with:

- Arrow keys → motor control
- Page Up/Down, Home/End → servo aiming
- S/P → start/pause autonomous scan-and-push mode
- Space → 5-second pause
- Escape → stop and exit

Autonomous mode: `scan()` → `optimal_angle()` → `rotate()` → `forward/backward`
(depth-limited recursion).

### `server/app.py`

FastAPI application factory (`create_app()`):

- **Lifespan handler** tries to connect hardware (Arduino, camera, ML detector)
  on startup, stores them in `app.state`, tears down on shutdown. Missing
  hardware is tolerated — endpoints return HTTP 503.
- Mounts three routers under `/api/robot/`, `/api/detection/`, `/api/files/`
- Serves the Jinja2 dashboard at `/`

### `server/auth.py`

Bearer-token authentication using `fastapi.security.HTTPBearer`. Validates
against `Settings.auth_token` with constant-time comparison (`hmac.compare_digest`).

### `server/routes/robot.py`

Motor, servo, and sensor REST endpoints. All require authentication. Motor
actions are dispatched dynamically by name. Sensor endpoints accept query
parameters matching `ScanConfig`.

### `server/routes/detection.py`

Colour detection (GET with optional HSV override query params) and ML
detection (train, predict, status). Uses `ColorDetector` and `CubeDetector`
from `app.state`.

### `server/routes/files.py`

Authenticated file upload, listing, execution, and deletion. Security measures:

- Path traversal prevention (`_safe_script_path()`)
- `.py`-only restriction
- 1 MiB upload limit
- Timeout-limited subprocess execution
- Sandboxed to the `uploads/` directory

### `gui/control_panel.py` — `ControlPanel`

Modern Tkinter GUI with ttk styling (Catppuccin-inspired dark theme):

- Directional button grid + servo controls
- Start/Pause/Stop mode buttons
- Resizable sensor bar-chart canvas
- Keyboard dispatch via keysym-to-keycode mapping (platform-portable)
- Status bar with OK/warning colours

## Data flow diagrams

### ML strategy flow

```
┌─────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────┐
│  Servos  │────▶│  Sensor   │────▶│  CubeDetector│────▶│  Motors  │
│ (sweep)  │     │ (scan_3d) │     │  (predict)   │     │ (act)    │
└─────────┘     └───────────┘     └──────────────┘     └──────────┘
                                         │
                                    True: forward(5)
                                    False: random move
```

### Vision strategy flow

```
┌───────────────┐     ┌──────────┐     ┌──────────┐
│ Vision Server │────▶│ Distance │────▶│  Motors  │
│  (HTTP GET)   │     │  compare │     │  (act)   │
└───────────────┘     └──────────┘     └──────────┘
                           │
                      d2 > d1: backward
                      else: forward
```

### Server request flow

```
Client ──▶ FastAPI ──▶ auth.require_auth() ──▶ Router
                                                  │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                        robot_router        detection_router      files_router
                              │                    │                    │
                              ▼                    ▼                    ▼
                      MotorController       ColorDetector         uploads/ dir
                      ServoController       CubeDetector          subprocess
                      UltrasonicSensor
```

## Configuration reference

All settings are loaded from environment variables with the `MECH_` prefix.
Nested models use `__` as delimiter.

| Variable | Type | Default | Description |
|---|---|---|---|
| `MECH_SERIAL_PORT` | str | `/dev/ttyUSB0` | Arduino serial port |
| `MECH_BAUD_RATE` | int | `57600` | Serial baud rate |
| `MECH_SERVER_HOST` | str | `0.0.0.0` | FastAPI bind address |
| `MECH_SERVER_PORT` | int | `8000` | FastAPI bind port |
| `MECH_AUTH_TOKEN` | str | `changeme` | Bearer token for API auth |
| `MECH_CAMERA_INDEX` | int | `0` | OpenCV camera index |
| `MECH_VISION_SERVER_URL` | str | `http://localhost:80` | URL for vision strategy |
| `MECH_PINS__MOTOR_LEFT_FWD` | int | `9` | Left motor forward pin |
| `MECH_PINS__MOTOR_LEFT_BWD` | int | `8` | Left motor backward pin |
| `MECH_PINS__MOTOR_RIGHT_FWD` | int | `11` | Right motor forward pin |
| `MECH_PINS__MOTOR_RIGHT_BWD` | int | `10` | Right motor backward pin |
| `MECH_PINS__SERVO_HORIZONTAL` | int | `5` | Horizontal servo pin |
| `MECH_PINS__SERVO_VERTICAL` | int | `6` | Vertical servo pin |
| `MECH_PINS__ECHO` | int | `7` | Ultrasonic echo pin |
| `MECH_SCAN__ANGLE_MIN` | int | `0` | Scan start angle |
| `MECH_SCAN__ANGLE_MAX` | int | `130` | Scan end angle |
| `MECH_SCAN__ANGLE_STEP` | int | `13` | Degrees per scan step |
| `MECH_SCAN__DISTANCE_THRESHOLD` | float | `40.0` | Object detection threshold (cm) |
| `MECH_SCAN__PING_SAMPLES` | int | `3` | Readings per measurement |
| `MECH_HSV__H_MIN` | int | `0` | HSV hue minimum |
| `MECH_HSV__H_MAX` | int | `180` | HSV hue maximum |
| `MECH_HSV__S_MIN` | int | `0` | HSV saturation minimum |
| `MECH_HSV__S_MAX` | int | `255` | HSV saturation maximum |
| `MECH_HSV__V_MIN` | int | `0` | HSV value minimum |
| `MECH_HSV__V_MAX` | int | `255` | HSV value maximum |
| `MECH_ML__N_ESTIMATORS` | int | `10` | Boosting stages |
| `MECH_ML__LEARNING_RATE` | float | `0.1` | GradientBoosting learning rate |
| `MECH_ML__MAX_DEPTH` | int | `3` | Max tree depth |

## Testing strategy

Tests live in `tests/` and use mocked hardware so they run without an Arduino
or camera (including in CI).

| Test file | Covers |
|---|---|
| `conftest.py` | `MockPin`, `MockArduino`, `MockIterator` — lightweight fakes for pyfirmata; fixtures for `board`, `motor`, `servo`, `sensor`, `settings` |
| `test_motor.py` | Pin write sequences for every motor primitive and compound movement |
| `test_sensor.py` | Ping averaging, 2D scan structure, 3D scan detection logic (close/far/zero) |
| `test_ml_detector.py` | Init, fit metrics, predict before/after fit, `predict_from_scan` |
| `test_color_detector.py` | Camera lifecycle, frame capture errors, centroid calculation, multi-detect |
| `test_config.py` | Default values, env-var overrides, `get_settings()` caching |
| `test_server.py` | All REST endpoints via FastAPI TestClient — auth, motor, servo, sensor, colour, ML, files, dashboard |

## CI/CD pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **lint** job (Ubuntu, Python 3.14):
   - `ruff check src tests`
   - `ruff format --check src tests`

2. **test** job (Ubuntu, Python 3.14, runs after lint):
   - `pip install -e ".[dev,vision,server]"`
   - `pytest --tb=short -q`

Triggered on push/PR to `main`.

## Dependency groups

Defined in `pyproject.toml` optional-dependencies:

| Group | Packages | Purpose |
|---|---|---|
| (core) | pyfirmata, numpy, scikit-learn, pydantic-settings | Always installed |
| `vision` | opencv-python | Camera-based colour detection |
| `server` | fastapi, uvicorn[standard], jinja2, python-multipart | REST API + web dashboard |
| `dev` | pytest, ruff, pre-commit, httpx | Development and testing |
