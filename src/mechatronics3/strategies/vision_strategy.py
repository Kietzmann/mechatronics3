"""Camera-tracking approach/retreat strategy.

Ported from the original ``ArduinoRoboCar2.py``.  Fetches colour-detection
coordinates from a remote vision server (see
:mod:`mechatronics3.detection.color_detector` served via the FastAPI app),
computes the apparent distance between two tracked colour blobs, and drives
toward or away from the target.

Bug fix
-------
The original script called ``R(1)`` which was never defined, causing a
:exc:`NameError` at runtime.  Based on the approach/retreat intent of the
algorithm, the call has been replaced with ``motor.backward(1)`` — if the
apparent size of the target increases (d2 > d1) the robot retreats instead
of continuing forward.
"""

from __future__ import annotations

import logging
import math
import time
import urllib.request

from mechatronics3.config import get_settings
from mechatronics3.core import MotorController, RobotBoard

logger = logging.getLogger(__name__)


def _fetch_coordinates(url: str) -> tuple[int, int, int, int] | None:
    """Request colour-blob coordinates from the vision server.

    Returns ``(x1, y1, x2, y2)`` or ``None`` when no blobs are visible.
    """
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read().decode()
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Vision server unreachable: %s", exc)
        return None

    data = data.strip()
    if not data:
        return None

    parts = data.split()
    if len(parts) != 4:
        logger.warning("Unexpected response from vision server: %r", data)
        return None

    x1, y1, x2, y2 = (int(v) for v in parts)
    return x1, y1, x2, y2


def _distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Euclidean distance between two points."""
    return math.hypot(x2 - x1, y2 - y1)


def run() -> None:
    """Main vision-tracking loop: measure → drive → re-measure → decide."""
    settings = get_settings()
    pins = settings.pins

    with RobotBoard(settings.serial_port, settings.baud_rate) as board:
        board.setup_pins(pins)
        motor = MotorController(
            board,
            lf_pin=pins.motor_left_fwd,
            lb_pin=pins.motor_left_bwd,
            rf_pin=pins.motor_right_fwd,
            rb_pin=pins.motor_right_bwd,
            motor_config=settings.motor,
        )

        try:
            while True:
                data = _fetch_coordinates(settings.vision_server_url)
                if data is None:
                    time.sleep(2)
                    continue

                x1, y1, x2, y2 = data
                d1 = _distance(x1, y1, x2, y2)

                motor.forward(1)

                data = _fetch_coordinates(settings.vision_server_url)
                if data is None:
                    time.sleep(2)
                    continue

                x1, y1, x2, y2 = data
                d2 = _distance(x1, y1, x2, y2)

                if d2 > d1:
                    # Original bug: called R(1) which was undefined.
                    # Retreat when the target appears larger (robot is closer).
                    motor.backward(1)
                else:
                    motor.forward(1)

                time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Vision strategy stopped")
            motor.stop()
