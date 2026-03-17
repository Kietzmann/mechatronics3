"""Motor control abstraction."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyfirmata import Pin

    from mechatronics3.core.board import RobotBoard


class MotorController:
    """Drive left/right DC motors via four digital-output pins.

    The original wiring convention (and default :class:`~mechatronics3.config.PinMap`)::

        Left  motor: pin 8 (backward) / pin 9 (forward)
        Right motor: pin 10 (backward) / pin 11 (forward)

    Parameters
    ----------
    board:
        An initialised :class:`~mechatronics3.core.board.RobotBoard`.
    lf_pin, lb_pin:
        Pin numbers for left-motor forward / backward.
    rf_pin, rb_pin:
        Pin numbers for right-motor forward / backward.
    """

    def __init__(
        self,
        board: RobotBoard,
        *,
        lf_pin: int = 9,
        lb_pin: int = 8,
        rf_pin: int = 11,
        rb_pin: int = 10,
    ) -> None:
        self._lf: Pin = board.digital_output(lf_pin)
        self._lb: Pin = board.digital_output(lb_pin)
        self._rf: Pin = board.digital_output(rf_pin)
        self._rb: Pin = board.digital_output(rb_pin)

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def stop(self, duration: float = 0) -> None:
        """Deactivate all motor pins, then optionally sleep *duration* seconds."""
        self._lf.write(0)
        self._lb.write(0)
        self._rf.write(0)
        self._rb.write(0)
        if duration > 0:
            time.sleep(duration)

    def right_forward(self, duration: float, *, auto_stop: bool = True) -> None:
        """Run the right motor forward for *duration* seconds."""
        self._rb.write(0)
        self._rf.write(1)
        time.sleep(duration)
        if auto_stop:
            self.stop()

    def right_backward(self, duration: float, *, auto_stop: bool = True) -> None:
        """Run the right motor backward for *duration* seconds."""
        self._rf.write(0)
        self._rb.write(1)
        time.sleep(duration)
        if auto_stop:
            self.stop()

    def left_forward(self, duration: float, *, auto_stop: bool = True) -> None:
        """Run the left motor forward for *duration* seconds."""
        self._lb.write(0)
        self._lf.write(1)
        time.sleep(duration)
        if auto_stop:
            self.stop()

    def left_backward(self, duration: float, *, auto_stop: bool = True) -> None:
        """Run the left motor backward for *duration* seconds."""
        self._lf.write(0)
        self._lb.write(1)
        time.sleep(duration)
        if auto_stop:
            self.stop()

    # ------------------------------------------------------------------
    # Compound movements
    # ------------------------------------------------------------------

    def forward(self, duration: float) -> None:
        """Drive both motors forward for *duration* seconds.

        A small lead-in on the right motor compensates for uneven torque,
        matching the behaviour of the original ``F()`` helper.
        """
        self.right_forward(0.1, auto_stop=False)
        self.left_forward(duration)
        self.stop()

    def backward(self, duration: float) -> None:
        """Drive both motors backward for *duration* seconds."""
        self.right_backward(0.1, auto_stop=False)
        self.left_backward(duration)
        self.stop()

    def rotate(self, angle: float, angle_range: float = 130.0) -> None:
        """Rotate in-place toward *angle* within [0, *angle_range*].

        If *angle* falls in the first half of the range the robot turns left;
        otherwise it turns right.  The empirical coefficient ``k`` converts
        angle to duration (seconds) and should be tuned for each chassis.
        """
        k = 0.01
        midpoint = angle_range / 2.0
        if 0 <= angle <= midpoint:
            self.left_forward(angle * k)
        elif midpoint < angle <= angle_range:
            self.right_forward((angle - midpoint) * k)
