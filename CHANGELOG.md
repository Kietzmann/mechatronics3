# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] — 2026-03-17

Complete rewrite of the project from flat Python 2 scripts to a modern,
industry-standard Python 3.14 package.

### Project structure

**Before:** Five standalone scripts in the repository root with no package
structure, no dependency management, no tests, and no CI/CD.

```
ArduinoRoboCar.py       → ML-based autonomous strategy
ArduinoRoboCar2.py      → Vision-based strategy (Python 2, urllib2)
ArduinoRoboCar3.py      → Manual GUI control (Python 2, Tkinter)
cv2detectColor2web.py   → Bottle server for colour detection
server.py               → Bottle file upload/execution demo
README.md               → Ukrainian README
LICENSE                  → GPL v3
mindmap.md              → Mermaid mindmap
```

**After:** PEP 621 package using `src/` layout with hatchling build backend.

```
src/mechatronics3/
├── config.py           (NEW) pydantic-settings configuration
├── core/               (NEW) board, motor, sensor, servo abstractions
├── detection/          (NEW) ML detector + OpenCV colour detector
├── strategies/         (PORTED) ml, vision, manual — using shared core
├── server/             (NEW) FastAPI REST API + web dashboard
├── gui/                (NEW) Modernised tkinter control panel
└── __main__.py         (NEW) CLI entry point
```

### Python 2 → 3.14 migration

- Replaced `print` statements with `print()` function calls
- Replaced `urllib2` with `urllib.request`
- Replaced `Tkinter` with `tkinter`
- Replaced `Bottle` with `FastAPI` + `uvicorn`
- Added type hints throughout all public APIs
- Added docstrings in English on all public classes and methods

### Shared code extraction

The three ArduinoRoboCar scripts shared approximately 80% of their code
(board initialisation, pin setup, motor functions, sensor functions). This
duplication was eliminated by extracting into reusable classes:

| Original code | New module | Class |
|---|---|---|
| Board init + pin setup | `core/board.py` | `RobotBoard` |
| Motor functions (stop, RF, LF, RB, LB, F, B) | `core/motor.py` | `MotorController` |
| Servo pin writes | `core/servo.py` | `ServoController` |
| Ultrasonic ping/scan/scan3D | `core/sensor.py` | `UltrasonicSensor` |
| GradientBoostingClassifier training | `detection/ml_detector.py` | `CubeDetector` |
| OpenCV colour detection | `detection/color_detector.py` | `ColorDetector` |

### Bug fixes

- **`ArduinoRoboCar2.py` — undefined `R()` call**: The original script called
  `R(1)` on line 131 which was never defined, causing a `NameError` at
  runtime. Replaced with `motor.backward(1)` based on the approach/retreat
  intent of the algorithm (retreat when the target appears larger).

### Configuration management

Replaced all hardcoded values with centralised `pydantic-settings` configuration:

| Hardcoded value | New config |
|---|---|
| `COM25`, `COM14`, `COM7` serial ports | `MECH_SERIAL_PORT` env var |
| `57600` baud rate | `MECH_BAUD_RATE` env var |
| `192.168.0.101` IP address | `MECH_VISION_SERVER_URL` env var |
| Pin numbers 5, 6, 7, 8, 9, 10, 11 | `MECH_PINS__*` env vars |
| Hardcoded passwords `111`, `222`, `333` | `MECH_AUTH_TOKEN` (bearer token) |

### New features

#### FastAPI REST API server

Replaced `server.py` (Bottle, hardcoded passwords, runs arbitrary code via
`c:/python27/python.exe`) and `cv2detectColor2web.py` (Bottle, binds to
specific IP) with a modern FastAPI application:

- **Motor control** — `POST /api/robot/motor/{action}` for all motor commands
- **Servo control** — `POST /api/robot/servo/horizontal|vertical|center`,
  `GET /api/robot/servo`
- **Sensor** — `GET /api/robot/sensor/ping|scan|scan3d`
- **Colour detection** — `GET /api/detection/color` with optional HSV overrides
- **ML detection** — `POST /api/detection/ml/train|predict`,
  `GET /api/detection/ml/status`
- **File management** — `GET/POST/DELETE /api/files/` with upload, execute,
  delete
- **Web dashboard** — Single-page HTML UI at `/` with motor controls, servo
  sliders, sensor readouts, colour detection, ML prediction, and file management
- **Authentication** — Bearer token via `Authorization` header with
  constant-time comparison
- **Security** — path traversal prevention, `.py`-only uploads, 1 MiB file
  size limit, timeout-limited subprocess execution
- **Graceful degradation** — server starts without hardware, returns HTTP 503
  for hardware-dependent endpoints

#### Modernised tkinter GUI

Replaced the minimal Python 2 Tkinter GUI with a styled, dark-themed control
panel using ttk:

- Catppuccin-inspired colour palette
- Directional button grid + servo control buttons
- Start/Pause/Stop mode buttons
- Resizable sensor bar-chart canvas
- Platform-portable keyboard dispatch via keysym mapping
- Status bar with contextual colours

#### CLI entry point

Added `mechatronics3` command with four sub-commands:

```
mechatronics3 server    # Start FastAPI web server
mechatronics3 ml        # Run autonomous ML strategy
mechatronics3 vision    # Run camera-tracking strategy
mechatronics3 manual    # Run manual GUI control
```

### Dependency management

Added `pyproject.toml` (PEP 621) with hatchling build backend:

- **Core**: pyfirmata, numpy, scikit-learn, pydantic-settings
- **vision**: opencv-python (optional)
- **server**: fastapi, uvicorn[standard], jinja2, python-multipart (optional)
- **dev**: pytest, ruff, pre-commit, httpx (optional)

### Testing

Added comprehensive test suite in `tests/` with mocked hardware:

- `conftest.py` — `MockPin`, `MockArduino`, `MockIterator` fakes for pyfirmata;
  reusable fixtures for board, motor, servo, sensor, settings
- `test_motor.py` — 11 tests covering pin write sequences for every motor
  primitive and compound movement
- `test_sensor.py` — 7 tests covering ping averaging, scan structure, and 3D
  scan detection logic (close/far/zero distance)
- `test_ml_detector.py` — 7 tests covering init, training metrics, prediction
  before/after fit, and scan-based prediction
- `test_color_detector.py` — 7 tests covering camera lifecycle, frame capture
  errors, centroid calculation, and multi-colour detection
- `test_config.py` — 10 tests covering default values, env-var overrides, and
  settings caching
- `test_server.py` — 20 tests covering all REST endpoints via FastAPI
  TestClient (auth, motor, servo, sensor, colour, ML, files, dashboard)

### CI/CD

Added GitHub Actions workflow (`.github/workflows/ci.yml`):

- **lint** job: `ruff check` + `ruff format --check`
- **test** job: `pytest` with all optional dependencies
- Runs on push/PR to `main`, Python 3.14, Ubuntu latest

### Code quality

- Ruff for linting and formatting (line length 131, rules: E, W, F, I, UP, B,
  SIM, RUF)
- Pre-commit hooks: trailing whitespace, end-of-file fixer, YAML check, black,
  isort, pycln, ruff check, ruff format
- `.gitignore` covering `__pycache__`, dist, venv, IDE files, `.env`,
  pytest/coverage artifacts

### Documentation

All documentation translated from Ukrainian to English:

- `README.md` — Project overview, architecture tree, quick start, configuration
  table, development instructions, links to detailed docs
- `docs/getting-started.md` — Prerequisites, installation, configuration,
  running each mode, testing, troubleshooting
- `docs/hardware-setup.md` — Bill of materials, firmware flashing, pin mapping
  table, ASCII wiring diagram, motor direction truth table, servo range,
  sensor mounting, supported boards, power considerations, wireless operation
- `docs/api-reference.md` — Full REST API documentation with request/response
  examples for every endpoint
- `docs/architecture.md` — Internal architecture, module descriptions, data
  flow diagrams, configuration reference, testing strategy, CI/CD pipeline

### Files retained (legacy)

The original scripts are preserved in the repository root for reference:

- `ArduinoRoboCar.py` — original ML strategy (Python 2)
- `ArduinoRoboCar2.py` — original vision strategy (Python 2, contains R() bug)
- `ArduinoRoboCar3.py` — original manual GUI (Python 2)
- `cv2detectColor2web.py` — original Bottle colour detection server
- `server.py` — original Bottle file upload server
- `mindmap.md` — original project planning mindmap (Ukrainian)

These are excluded from pre-commit hooks via the `.pre-commit-config.yaml`
`exclude` pattern.
