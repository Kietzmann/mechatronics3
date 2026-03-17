"""Centralised configuration backed by environment variables / ``.env`` file."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class PinMap(BaseModel):
    """Arduino digital-pin assignments.

    Default wiring (matching the original ArduinoRoboCar hardware)::

        Left  motor: pins 8 (bwd) / 9 (fwd)
        Right motor: pins 10 (bwd) / 11 (fwd)
        Horizontal servo: pin 5
        Vertical   servo: pin 6
        Ultrasonic echo:  pin 7
    """

    motor_left_fwd: int = 9
    motor_left_bwd: int = 8
    motor_right_fwd: int = 11
    motor_right_bwd: int = 10
    servo_horizontal: int = 5
    servo_vertical: int = 6
    echo: int = 7


class HSVRange(BaseModel):
    """HSV colour-detection thresholds."""

    h_min: int = 0
    h_max: int = 180
    s_min: int = 0
    s_max: int = 255
    v_min: int = 0
    v_max: int = 255


class ScanConfig(BaseModel):
    """Ultrasonic scan sweep parameters."""

    angle_min: int = 0
    angle_max: int = 130
    angle_step: int = 13
    vertical_angles: tuple[int, ...] = (110, 60)
    distance_threshold: float = 40.0
    ping_samples: int = 3


class MLConfig(BaseModel):
    """GradientBoosting classifier hyper-parameters."""

    n_estimators: int = 10
    learning_rate: float = 0.1
    max_depth: int = 3


class Settings(BaseSettings):
    """Application-wide settings.

    Override any field via the corresponding ``MECH_``-prefixed environment
    variable.  Nested models use ``__`` as the delimiter, e.g.
    ``MECH_PINS__ECHO=7``.

    A ``.env`` file in the working directory is loaded automatically when
    present.
    """

    model_config = SettingsConfigDict(
        env_prefix="MECH_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 57600

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    auth_token: str = "changeme"

    camera_index: int = 0
    vision_server_url: str = "http://localhost:80"

    pins: PinMap = PinMap()
    hsv: HSVRange = HSVRange()
    scan: ScanConfig = ScanConfig()
    ml: MLConfig = MLConfig()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton :class:`Settings` instance."""
    return Settings()
