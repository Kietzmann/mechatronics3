# Getting started

This guide walks you through installing mechatronics3, connecting to your
Arduino robot, and running each of the four operating modes.

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python >= 3.14** | CPython only (pyFirmata uses serial I/O) |
| **Arduino board** | Uno, Mega, or any pyFirmata-compatible board |
| **StandardFirmata** | Upload the sketch via the Arduino IDE before first use |
| **USB cable** | Or a wireless serial bridge (Bluetooth/HC-05, ESP-link, etc.) |

Optional (for specific features):

| Requirement | Needed for |
|---|---|
| **USB camera / webcam** | Vision strategy, colour detection API |
| **HC-SR04 ultrasonic sensor** | Sensor ping / scan / scan_3d |
| **Two DC motors + L298N driver** | Motor control |
| **Two micro-servos (SG90)** | Horizontal + vertical aiming |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/vkopey/mechatronics3.git
cd mechatronics3
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
```

### 3. Install the package

Pick one of the following depending on which features you need:

```bash
# Core only (motor, sensor, servo, ML detector)
pip install -e .

# Core + camera / OpenCV
pip install -e ".[vision]"

# Core + web server
pip install -e ".[server]"

# Everything (recommended for development)
pip install -e ".[dev,vision,server]"
```

### 4. Flash StandardFirmata onto the Arduino

1. Open the Arduino IDE.
2. Go to **File > Examples > Firmata > StandardFirmata**.
3. Select your board and port under **Tools**.
4. Click **Upload**.

The board must be running StandardFirmata for pyFirmata to communicate with it.

## Configuration

mechatronics3 reads settings from environment variables (prefixed `MECH_`) or a
`.env` file in the project root.

Create a `.env` file to avoid typing variables every time:

```dotenv
MECH_SERIAL_PORT=/dev/ttyUSB0     # Linux
# MECH_SERIAL_PORT=COM3            # Windows
MECH_BAUD_RATE=57600
MECH_AUTH_TOKEN=my-secret-token
MECH_CAMERA_INDEX=0
```

Pin assignments can be overridden with the nested `MECH_PINS__*` variables:

```dotenv
MECH_PINS__MOTOR_LEFT_FWD=9
MECH_PINS__MOTOR_LEFT_BWD=8
MECH_PINS__MOTOR_RIGHT_FWD=11
MECH_PINS__MOTOR_RIGHT_BWD=10
MECH_PINS__SERVO_HORIZONTAL=5
MECH_PINS__SERVO_VERTICAL=6
MECH_PINS__ECHO=7
```

See the full list of settings in `src/mechatronics3/config.py`.

## Running

The `mechatronics3` CLI provides four sub-commands.

### Manual control (tkinter GUI)

```bash
mechatronics3 manual
```

Opens a tkinter window with:

- **Arrow keys** — forward, backward, left-forward, right-forward
- **Page Up / Page Down** — left-backward / right-backward
- **Home / End** — aim servo left / right
- **Space** — stop motors
- **S** — run an ultrasonic scan (results shown in the bar chart)
- **P** — scan-and-push: find the nearest object, rotate toward it, drive
  forward
- **Escape** — quit

### Vision strategy

```bash
mechatronics3 vision
```

Connects to a colour-detection server (see `MECH_VISION_SERVER_URL`, default
`http://localhost:80`) and uses the reported bounding box to approach or retreat
from the detected object.

### ML strategy

```bash
mechatronics3 ml
```

Trains a GradientBoosting classifier on built-in training data, then loops:

1. Perform a 3-D ultrasonic scan.
2. Feed the detection vector to the model.
3. If an object is predicted — drive forward.
4. Otherwise — make a random exploratory move.

### Web server

```bash
mechatronics3 server
```

Starts a FastAPI server (default `http://0.0.0.0:8000`) with:

- **Web dashboard** at `/` — motor buttons, servo sliders, sensor readouts
- **REST API** under `/api/robot/`, `/api/detection/`, `/api/files/`
- **Interactive docs** at `/docs` (Swagger UI)

All API endpoints require a Bearer token matching `MECH_AUTH_TOKEN`.

## Running tests

```bash
pip install -e ".[dev,vision,server]"
pytest
```

Tests use mocked hardware so no Arduino or camera is needed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Permission denied` on serial port | Add your user to the `dialout` group: `sudo usermod -aG dialout $USER`, then log out and back in |
| `serial.serialutil.SerialException` | Check `MECH_SERIAL_PORT` matches the actual device (`ls /dev/tty*`) |
| `Hardware not available` from the server | The server starts without hardware and returns HTTP 503 for robot endpoints; connect the Arduino and restart |
| `Camera is not open` | Set `MECH_CAMERA_INDEX` to the correct device; run `ls /dev/video*` to list cameras |
| Import errors for `cv2` | Install the vision extra: `pip install -e ".[vision]"` |
| Import errors for `fastapi` | Install the server extra: `pip install -e ".[server]"` |
