# API reference

mechatronics3 exposes a REST API via FastAPI. Start the server with:

```bash
mechatronics3 server
```

The server binds to `MECH_SERVER_HOST`:`MECH_SERVER_PORT` (default
`0.0.0.0:8000`). Interactive Swagger documentation is available at
[http://localhost:8000/docs](http://localhost:8000/docs).

## Authentication

All API endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The expected token is set via the `MECH_AUTH_TOKEN` environment variable
(default: `changeme`). Requests with a missing or incorrect token receive a
`401 Unauthorized` response.

---

## Web dashboard

### `GET /`

Serves the single-page HTML dashboard with motor controls, servo sliders,
sensor readouts, colour detection, ML detection, and file management. No
authentication is required for the dashboard page itself (API calls made from
the dashboard do require the token).

---

## Robot control

All robot endpoints live under `/api/robot/`.

### Motor

#### `POST /api/robot/motor/{action}`

Execute a motor command.

**Path parameters:**

| Name | Type | Description |
|---|---|---|
| `action` | string | One of: `forward`, `backward`, `left_forward`, `left_backward`, `right_forward`, `right_backward`, `stop`, `rotate` |

**Request body** (`application/json`):

| Field | Type | Default | Description |
|---|---|---|---|
| `duration` | float | `1.0` | Seconds to drive (0–30). Used by all actions except `rotate`. |
| `angle` | float \| null | `null` | Target angle in degrees (0–180). Required for `rotate`. |
| `angle_range` | float | `130.0` | Full sweep range for `rotate` (>= 1). |

**Example — drive forward for 2 seconds:**

```bash
curl -X POST http://localhost:8000/api/robot/motor/forward \
  -H "Authorization: Bearer changeme" \
  -H "Content-Type: application/json" \
  -d '{"duration": 2.0}'
```

**Response** (`200 OK`):

```json
{"status": "ok", "action": "forward", "duration": 2.0}
```

**Example — rotate toward 45 degrees:**

```bash
curl -X POST http://localhost:8000/api/robot/motor/rotate \
  -H "Authorization: Bearer changeme" \
  -H "Content-Type: application/json" \
  -d '{"angle": 45.0}'
```

**Response:**

```json
{"status": "ok", "action": "rotate", "angle": 45.0}
```

**Errors:**

| Code | Condition |
|---|---|
| 422 | Unknown action or missing `angle` for `rotate` |
| 503 | Hardware not connected |

---

### Servo

#### `POST /api/robot/servo/horizontal`

Set the horizontal servo angle.

**Request body:**

| Field | Type | Description |
|---|---|---|
| `angle` | float | Target angle (0–180) |

**Response** (`200 OK`):

```json
{"status": "ok", "angle": 65.0}
```

#### `POST /api/robot/servo/vertical`

Set the vertical servo angle. Same request/response format as horizontal.

#### `POST /api/robot/servo/center`

Move both servos to their center positions (horizontal 65°, vertical 90°).

**Response** (`200 OK`):

```json
{"status": "ok"}
```

#### `GET /api/robot/servo`

Read the current servo positions.

**Response** (`200 OK`):

```json
{"horizontal": 65.0, "vertical": 90.0}
```

---

### Sensor

#### `GET /api/robot/sensor/ping`

Take a single distance measurement.

**Query parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `samples` | int | `3` | Number of readings to average (1–20) |

**Response** (`200 OK`):

```json
{"distance_cm": 24.5}
```

#### `GET /api/robot/sensor/scan`

Sweep the horizontal servo and measure distance at each step (2-D scan).

**Query parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `angle_min` | int | `0` | Start angle (>= 0) |
| `angle_max` | int | `130` | End angle (<= 180) |
| `angle_step` | int | `13` | Degrees between measurements (>= 1) |
| `samples` | int | `3` | Readings per step (1–20) |

**Response** (`200 OK`):

```json
{
  "angles": [0.0, 13.0, 26.0, 39.0, 52.0, 65.0, 78.0, 91.0, 104.0, 117.0, 130.0],
  "distances": [42.1, 38.5, 35.0, 22.3, 18.7, 15.2, 19.8, 28.4, 33.6, 40.1, 45.0]
}
```

#### `GET /api/robot/sensor/scan3d`

Sweep both servos for a 3-D detection grid. Each cell is flagged `1` if the
measured distance is below the threshold and non-zero.

**Query parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `angle_min` | int | `0` | Horizontal start angle |
| `angle_max` | int | `130` | Horizontal end angle |
| `angle_step` | int | `13` | Horizontal step |
| `distance_threshold` | float | `40.0` | Object detection threshold (cm) |
| `samples` | int | `3` | Readings per cell |

**Response** (`200 OK`):

```json
{
  "horizontal": [0.0, 13.0, 26.0, 39.0, 52.0, 65.0, 78.0, 91.0, 104.0, 117.0, 130.0,
                  0.0, 13.0, 26.0, 39.0, 52.0, 65.0, 78.0, 91.0, 104.0, 117.0, 130.0],
  "vertical":   [110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0,
                  60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0],
  "detections": [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0,
                 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
}
```

---

## Detection

All detection endpoints live under `/api/detection/`.

### Colour detection

#### `GET /api/detection/color`

Capture a camera frame and detect the centroid of a colour region using HSV
thresholding.

**Query parameters** (all optional — defaults come from `Settings.hsv`):

| Name | Type | Range | Description |
|---|---|---|---|
| `h_min` | int | 0–180 | Minimum hue |
| `h_max` | int | 0–180 | Maximum hue |
| `s_min` | int | 0–255 | Minimum saturation |
| `s_max` | int | 0–255 | Maximum saturation |
| `v_min` | int | 0–255 | Minimum value |
| `v_max` | int | 0–255 | Maximum value |

**Response — colour detected** (`200 OK`):

```json
{"detected": true, "x": 320, "y": 240}
```

**Response — no match:**

```json
{"detected": false, "x": null, "y": null}
```

---

### ML detection

#### `POST /api/detection/ml/train`

Train the GradientBoosting cube detector.

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `x` | list[list[int]] | — | Feature matrix. Each row is a binary detection vector. |
| `y` | list[int] | — | Labels (`1` = object present, `0` = empty). |
| `test_size` | float | `0.1` | Fraction held out for test accuracy. |
| `cv_folds` | int | `9` | Cross-validation folds. |

**Example:**

```bash
curl -X POST http://localhost:8000/api/detection/ml/train \
  -H "Authorization: Bearer changeme" \
  -H "Content-Type: application/json" \
  -d '{
    "x": [[0,0,1,1,1,0,0,0,0,0, 0,0,1,1,0,0,0,0,0,0],
           [0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0]],
    "y": [1, 0]
  }'
```

**Response** (`200 OK`):

```json
{
  "accuracy": 1.0,
  "cross_val_mean": 0.95,
  "cross_val_scores": [1.0, 0.9, 1.0, 0.9, 1.0, 0.9, 1.0, 0.9, 1.0]
}
```

#### `POST /api/detection/ml/predict`

Predict whether a detection vector indicates an object.

**Request body:**

| Field | Type | Description |
|---|---|---|
| `detections` | list[int] | Binary detection vector (same length as training features) |

**Response** (`200 OK`):

```json
{"object_detected": true}
```

**Errors:**

| Code | Condition |
|---|---|
| 400 | Model has not been trained yet |

#### `GET /api/detection/ml/status`

Check whether the ML model has been trained.

**Response** (`200 OK`):

```json
{"is_fitted": false}
```

---

## File management

All file endpoints live under `/api/files/`. They manage uploaded Python
scripts in the server's `uploads/` directory.

#### `GET /api/files/`

List all uploaded scripts.

**Response** (`200 OK`):

```json
[
  {"name": "my_script.py", "size": 1234},
  {"name": "test_algo.py", "size": 567}
]
```

#### `POST /api/files/upload`

Upload a Python script (max 1 MiB).

**Request:** `multipart/form-data` with a `file` field.

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -H "Authorization: Bearer changeme" \
  -F "file=@my_script.py"
```

**Response** (`200 OK`):

```json
{"status": "ok", "filename": "my_script.py", "size": 1234}
```

**Errors:**

| Code | Condition |
|---|---|
| 413 | File exceeds 1 MiB limit |
| 422 | Missing filename or non-`.py` extension |

#### `POST /api/files/execute`

Execute an uploaded script in a subprocess.

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `filename` | string | — | Name of the uploaded script |
| `timeout` | int | `30` | Maximum execution time in seconds (1–300) |

**Response** (`200 OK`):

```json
{
  "exit_code": 0,
  "stdout": "Hello from the robot!\n",
  "stderr": ""
}
```

**Errors:**

| Code | Condition |
|---|---|
| 404 | Script not found |
| 408 | Execution timed out |
| 422 | Invalid filename |

#### `DELETE /api/files/{filename}`

Delete an uploaded script.

**Response** (`200 OK`):

```json
{"status": "ok", "filename": "my_script.py"}
```

**Errors:**

| Code | Condition |
|---|---|
| 404 | Script not found |
| 422 | Invalid filename |

---

## Error responses

All error responses follow the standard FastAPI format:

```json
{"detail": "Human-readable error message"}
```

Common status codes across all endpoints:

| Code | Meaning |
|---|---|
| 401 | Missing or invalid Bearer token |
| 503 | Hardware or camera not connected (server started without Arduino/webcam) |
