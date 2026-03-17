"""Servo control abstraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyfirmata import Pin

    from mechatronics3.core.board import RobotBoard


class ServoController:
    """High-level wrapper around the horizontal and vertical servo pins.

    Parameters
    ----------
    board:
        An initialised :class:`~mechatronics3.core.board.RobotBoard`.
    h_pin:
        Digital pin number for the horizontal servo (default ``5``).
    v_pin:
        Digital pin number for the vertical servo (default ``6``).
    """

    def __init__(
        self,
        board: RobotBoard,
        *,
        h_pin: int = 5,
        v_pin: int = 6,
    ) -> None:
        self._h_servo: Pin = board.servo_pin(h_pin)
        self._v_servo: Pin = board.servo_pin(v_pin)

    # ------------------------------------------------------------------
    # Horizontal
    # ------------------------------------------------------------------

    def write_horizontal(self, angle: float) -> None:
        """Set the horizontal servo to *angle* degrees."""
        self._h_servo.write(angle)

    def read_horizontal(self) -> float | None:
        """Return the last-written horizontal angle (may be ``None``)."""
        return self._h_servo.read()

    # ------------------------------------------------------------------
    # Vertical
    # ------------------------------------------------------------------

    def write_vertical(self, angle: float) -> None:
        """Set the vertical servo to *angle* degrees."""
        self._v_servo.write(angle)

    def read_vertical(self) -> float | None:
        """Return the last-written vertical angle (may be ``None``)."""
        return self._v_servo.read()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def center(self, h_angle: float = 65.0, v_angle: float = 90.0) -> None:
        """Move both servos to their center positions."""
        self.write_horizontal(h_angle)
        self.write_vertical(v_angle)
