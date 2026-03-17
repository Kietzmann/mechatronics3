"""Manual scan-and-push with keyboard control.

Ported from the original ``ArduinoRoboCar3.py``.  Opens a tkinter window
with directional buttons and a sensor bar chart.  The user can drive the
robot manually via arrow keys or let it run in autonomous scan-and-push
mode (toggle with **S** to start / **P** to pause).

Keyboard bindings
-----------------
* Arrow keys — manual drive
* Page Up / Page Down — tilt horizontal servo
* Home / End — tilt vertical servo
* Space — pause for 5 seconds
* S — start autonomous mode
* P — pause autonomous mode
* Escape — stop motors and exit
"""

from __future__ import annotations

import logging
import random
import time

from mechatronics3.config import get_settings
from mechatronics3.core import (
    MotorController,
    RobotBoard,
    ServoController,
    UltrasonicSensor,
)
from mechatronics3.gui.control_panel import (
    KEY_DOWN,
    KEY_END,
    KEY_ESCAPE,
    KEY_HOME,
    KEY_LEFT,
    KEY_P,
    KEY_PAGE_DOWN,
    KEY_PAGE_UP,
    KEY_RIGHT,
    KEY_S,
    KEY_SPACE,
    KEY_UP,
    ControlPanel,
)

logger = logging.getLogger(__name__)

_SERVO_STEP = 10.0
_MANUAL_DRIVE_DURATION = 0.2
_SCAN_SETTLE = 0.9


def _optimal_angle(angles: list[float], detections: list[int]) -> float:
    """Return the median angle among those where an object was detected."""
    detected = [a for a, d in zip(angles, detections, strict=False) if d]
    return detected[len(detected) // 2]


def run() -> None:
    """Set up hardware and launch the tkinter control panel."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    pins = settings.pins
    auto_mode = False

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
        panel = ControlPanel()

        # ---- scan with GUI updates between steps ----

        def _scan_with_ui() -> tuple[list[float], list[int]]:
            """Sweep the sensor and update the panel between each step."""
            servo.write_vertical(70)
            angles: list[float] = []
            detections: list[int] = []
            angle = settings.scan.angle_min
            while angle <= settings.scan.angle_max:
                servo.write_horizontal(angle)
                time.sleep(_SCAN_SETTLE)
                dist = sensor.ping(settings.scan.ping_samples)
                angles.append(float(angle))
                detections.append(int(dist < settings.scan.distance_threshold and dist != 0))
                angle += settings.scan.angle_step
                panel.update()
            return angles, detections

        # ---- autonomous strategy (recursive, depth-limited) ----

        def strategy(depth: int = 0) -> None:
            angles, detections = _scan_with_ui()
            panel.visualize(detections)
            logger.info("Scan angles=%s detections=%s", angles, detections)

            if any(detections):
                angle = _optimal_angle(angles, detections)
                logger.info("Object at angle=%.0f", angle)
                motor.rotate(angle)
                if depth >= 1:
                    motor.forward(2)
                    motor.backward(2)
                else:
                    strategy(depth + 1)
            else:
                random_angle = 180 * random.random()
                motor.rotate(random_angle, angle_range=180.0)
                motor.forward(0.1)

        def auto_update() -> None:
            strategy()
            if auto_mode:
                panel.schedule(1000, auto_update)

        # ---- keyboard handler ----

        def on_key(keycode: int) -> None:
            nonlocal auto_mode

            action = None
            if keycode == KEY_RIGHT:
                action = motor.right_forward
            elif keycode == KEY_LEFT:
                action = motor.left_forward
            elif keycode == KEY_DOWN:
                action = motor.backward
            elif keycode == KEY_UP:
                action = motor.forward
            elif keycode == KEY_PAGE_DOWN:
                h = servo.read_horizontal()
                if h is not None:
                    servo.write_horizontal(h - _SERVO_STEP)
            elif keycode == KEY_PAGE_UP:
                h = servo.read_horizontal()
                if h is not None:
                    servo.write_horizontal(h + _SERVO_STEP)
            elif keycode == KEY_HOME:
                v = servo.read_vertical()
                if v is not None:
                    servo.write_vertical(v - _SERVO_STEP)
            elif keycode == KEY_END:
                v = servo.read_vertical()
                if v is not None:
                    servo.write_vertical(v + _SERVO_STEP)
            elif keycode == KEY_SPACE:
                time.sleep(5)
            elif keycode == KEY_P:
                auto_mode = False
                logger.info("Autonomous mode paused")
                panel.set_status("Paused", warn=True)
            elif keycode == KEY_S:
                auto_mode = True
                logger.info("Autonomous mode started")
                panel.set_status("Autonomous")
                auto_update()
            elif keycode == KEY_ESCAPE:
                motor.stop()
                panel.set_status("Stopped", warn=True)
                panel.destroy()
                return

            time.sleep(0.1)
            if action is not None:
                action(_MANUAL_DRIVE_DURATION)
                time.sleep(0.1)

        panel.set_key_handler(on_key)
        panel.schedule(0, auto_update)
        panel.run()
        motor.stop()
