"""Autonomous ML-based cube-pushing strategy.

Ported from the original ``ArduinoRoboCar.py``.  Uses a
:class:`~mechatronics3.detection.ml_detector.CubeDetector` trained on
pre-recorded 3-D ultrasonic scans.  The main loop performs a 3-D scan,
classifies the result, and either pushes forward (object found) or
moves randomly (nothing detected).
"""

from __future__ import annotations

import logging
import random

import numpy as np

from mechatronics3.config import get_settings
from mechatronics3.core import (
    MotorController,
    RobotBoard,
    ServoController,
    UltrasonicSensor,
)
from mechatronics3.detection.ml_detector import CubeDetector

logger = logging.getLogger(__name__)

# Pre-recorded training samples from the original script.
# Each row is a flattened binary detection vector from a 3-D scan (22 cells:
# 11 horizontal steps x 2 vertical angles).  Rows 0-8 have an object present
# at a single vertical level; rows 9-17 have detections at both levels;
# row 18 is empty; row 19 is fully occupied.
_TRAINING_X = np.array(
    [
        [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
)

_TRAINING_Y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])


def run() -> None:
    """Train the ML model on sample data, then loop: scan → predict → act."""
    logging.basicConfig(level=logging.INFO)
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
        )
        servo = ServoController(
            board,
            h_pin=pins.servo_horizontal,
            v_pin=pins.servo_vertical,
        )
        sensor = UltrasonicSensor(board, servo, echo_pin=pins.echo)

        detector = CubeDetector.from_config(settings.ml)
        result = detector.fit(_TRAINING_X, _TRAINING_Y)
        logger.info(
            "Model trained — accuracy: %.2f, CV mean: %.2f",
            result.accuracy,
            result.cross_val_mean,
        )

        try:
            while True:
                scan = sensor.scan_3d(
                    angle_min=settings.scan.angle_min,
                    angle_max=settings.scan.angle_max,
                    angle_step=settings.scan.angle_step,
                    vertical_angles=settings.scan.vertical_angles,
                    distance_threshold=settings.scan.distance_threshold,
                    samples=settings.scan.ping_samples,
                )
                if detector.predict_from_scan(scan):
                    logger.info("Object detected — pushing forward")
                    motor.forward(5)
                else:
                    direction = random.choice(
                        [motor.forward, motor.left_forward, motor.right_forward],
                    )
                    direction(random.random())
        except KeyboardInterrupt:
            logger.info("ML strategy stopped")
            motor.stop()
