"""REST endpoints for motor, servo, and sensor control."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mechatronics3.server.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

_DURATION_ACTIONS = frozenset(
    {
        "stop",
        "forward",
        "backward",
        "left_forward",
        "left_backward",
        "right_forward",
        "right_backward",
    }
)
_ALL_ACTIONS = sorted(_DURATION_ACTIONS | {"rotate"})


class MotorCommand(BaseModel):
    duration: float = Field(1.0, ge=0, le=30, description="Seconds to drive (or wait after stop)")
    angle: float | None = Field(None, ge=0, le=180, description="Target angle for rotate")
    angle_range: float = Field(130.0, ge=1, description="Full sweep range for rotate")


class ServoCommand(BaseModel):
    angle: float = Field(..., ge=0, le=180)


class ServoPosition(BaseModel):
    horizontal: float | None
    vertical: float | None


class PingResponse(BaseModel):
    distance_cm: float


class ScanResponse(BaseModel):
    angles: list[float]
    distances: list[float]


class Scan3DResponse(BaseModel):
    horizontal: list[float]
    vertical: list[float]
    detections: list[int]


# ---------------------------------------------------------------------------
# Hardware dependencies
# ---------------------------------------------------------------------------


def _get_motor(request: Request):
    motor = getattr(request.app.state, "motor", None)
    if motor is None:
        raise HTTPException(status_code=503, detail="Motor controller unavailable — hardware not connected")
    return motor


def _get_servo(request: Request):
    servo = getattr(request.app.state, "servo", None)
    if servo is None:
        raise HTTPException(status_code=503, detail="Servo controller unavailable — hardware not connected")
    return servo


def _get_sensor(request: Request):
    sensor = getattr(request.app.state, "sensor", None)
    if sensor is None:
        raise HTTPException(status_code=503, detail="Sensor unavailable — hardware not connected")
    return sensor


# ---------------------------------------------------------------------------
# Motor endpoints
# ---------------------------------------------------------------------------


@router.post("/motor/{action}", summary="Execute a motor command")
def motor_action(
    action: str,
    body: MotorCommand,
    motor=Depends(_get_motor),
) -> dict[str, object]:
    if action in _DURATION_ACTIONS:
        getattr(motor, action)(body.duration)
        return {"status": "ok", "action": action, "duration": body.duration}

    if action == "rotate":
        if body.angle is None:
            raise HTTPException(status_code=422, detail="'angle' is required for rotate")
        motor.rotate(body.angle, body.angle_range)
        return {"status": "ok", "action": action, "angle": body.angle}

    raise HTTPException(status_code=422, detail=f"Unknown action '{action}'. Valid: {_ALL_ACTIONS}")


# ---------------------------------------------------------------------------
# Servo endpoints
# ---------------------------------------------------------------------------


@router.post("/servo/horizontal", summary="Set horizontal servo angle")
def set_servo_horizontal(body: ServoCommand, servo=Depends(_get_servo)) -> dict[str, object]:
    servo.write_horizontal(body.angle)
    return {"status": "ok", "angle": body.angle}


@router.post("/servo/vertical", summary="Set vertical servo angle")
def set_servo_vertical(body: ServoCommand, servo=Depends(_get_servo)) -> dict[str, object]:
    servo.write_vertical(body.angle)
    return {"status": "ok", "angle": body.angle}


@router.post("/servo/center", summary="Center both servos")
def center_servos(servo=Depends(_get_servo)) -> dict[str, str]:
    servo.center()
    return {"status": "ok"}


@router.get("/servo", summary="Read current servo positions", response_model=ServoPosition)
def read_servos(servo=Depends(_get_servo)) -> ServoPosition:
    return ServoPosition(horizontal=servo.read_horizontal(), vertical=servo.read_vertical())


# ---------------------------------------------------------------------------
# Sensor endpoints
# ---------------------------------------------------------------------------


@router.get("/sensor/ping", summary="Single distance measurement", response_model=PingResponse)
def sensor_ping(
    samples: Annotated[int, Query(ge=1, le=20)] = 3,
    sensor=Depends(_get_sensor),
) -> PingResponse:
    return PingResponse(distance_cm=sensor.ping(samples))


@router.get("/sensor/scan", summary="2-D ultrasonic sweep", response_model=ScanResponse)
def sensor_scan(
    angle_min: Annotated[int, Query(ge=0)] = 0,
    angle_max: Annotated[int, Query(le=180)] = 130,
    angle_step: Annotated[int, Query(ge=1)] = 13,
    samples: Annotated[int, Query(ge=1, le=20)] = 3,
    sensor=Depends(_get_sensor),
) -> ScanResponse:
    result = sensor.scan(
        angle_min=angle_min,
        angle_max=angle_max,
        angle_step=angle_step,
        samples=samples,
    )
    return ScanResponse(angles=result.angles, distances=result.distances)


@router.get("/sensor/scan3d", summary="3-D ultrasonic sweep", response_model=Scan3DResponse)
def sensor_scan3d(
    angle_min: Annotated[int, Query(ge=0)] = 0,
    angle_max: Annotated[int, Query(le=180)] = 130,
    angle_step: Annotated[int, Query(ge=1)] = 13,
    distance_threshold: Annotated[float, Query(gt=0)] = 40.0,
    samples: Annotated[int, Query(ge=1, le=20)] = 3,
    sensor=Depends(_get_sensor),
) -> Scan3DResponse:
    result = sensor.scan_3d(
        angle_min=angle_min,
        angle_max=angle_max,
        angle_step=angle_step,
        distance_threshold=distance_threshold,
        samples=samples,
    )
    return Scan3DResponse(
        horizontal=result.horizontal,
        vertical=result.vertical,
        detections=result.detections,
    )
