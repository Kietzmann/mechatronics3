"""Ultrasonic sensor scanning."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pyfirmata import util

if TYPE_CHECKING:
    from pyfirmata import Pin

    from mechatronics3.core.board import RobotBoard
    from mechatronics3.core.servo import ServoController


@dataclass
class ScanResult:
    """Angles and corresponding distances from a 2-D sweep."""

    angles: list[float] = field(default_factory=list)
    distances: list[float] = field(default_factory=list)


@dataclass
class Scan3DResult:
    """Horizontal angles, vertical angles, and binary detection flags."""

    horizontal: list[float] = field(default_factory=list)
    vertical: list[float] = field(default_factory=list)
    detections: list[int] = field(default_factory=list)


class UltrasonicSensor:
    """Read distance via an ultrasonic echo pin and sweep with servos.

    Parameters
    ----------
    board:
        An initialised :class:`~mechatronics3.core.board.RobotBoard`.
    servo:
        A :class:`~mechatronics3.core.servo.ServoController` used to aim
        the sensor during scans.
    echo_pin:
        Digital pin number for the ultrasonic sensor (default ``7``).
    """

    def __init__(
        self,
        board: RobotBoard,
        servo: ServoController,
        *,
        echo_pin: int = 7,
    ) -> None:
        self._echo: Pin = board.digital_output(echo_pin)
        self._servo = servo

    # ------------------------------------------------------------------
    # Distance measurement
    # ------------------------------------------------------------------

    def ping(self, samples: int = 3) -> float:
        """Return the average distance (cm) over *samples* measurements."""
        total = sum(util.ping_time_to_distance(self._echo.ping()) for _ in range(samples))
        return total / samples

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(
        self,
        *,
        angle_min: int = 0,
        angle_max: int = 130,
        angle_step: int = 13,
        samples: int = 3,
        settle_time: float = 1.0,
    ) -> ScanResult:
        """Sweep the horizontal servo and measure distance at each step.

        Returns a :class:`ScanResult` containing parallel lists of angles and
        distances.
        """
        result = ScanResult()
        angle = angle_min
        while angle <= angle_max:
            self._servo.write_horizontal(angle)
            time.sleep(settle_time)
            dist = self.ping(samples)
            result.angles.append(float(angle))
            result.distances.append(dist)
            angle += angle_step
        return result

    def scan_3d(
        self,
        *,
        angle_min: int = 0,
        angle_max: int = 130,
        angle_step: int = 13,
        vertical_angles: tuple[int, ...] = (110, 60),
        distance_threshold: float = 40.0,
        samples: int = 3,
        h_settle: float = 1.0,
        v_settle: float = 0.01,
    ) -> Scan3DResult:
        """Sweep both servos and classify each reading as object / no-object.

        For each vertical angle the horizontal servo sweeps from *angle_min*
        to *angle_max*.  A reading is flagged ``1`` when the measured distance
        is below *distance_threshold* **and** non-zero.

        Returns a :class:`Scan3DResult` whose ``detections`` list can be fed
        directly into the ML classifier.
        """
        result = Scan3DResult()
        for v_angle in vertical_angles:
            self._servo.write_vertical(v_angle)
            time.sleep(v_settle)
            h_angle = angle_min
            while h_angle <= angle_max:
                self._servo.write_horizontal(h_angle)
                time.sleep(h_settle)
                dist = self.ping(samples)
                result.horizontal.append(float(h_angle))
                result.vertical.append(float(v_angle))
                result.detections.append(int(dist < distance_threshold and dist != 0))
                h_angle += angle_step
        return result
