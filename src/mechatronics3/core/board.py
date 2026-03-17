"""Arduino board connection and lifecycle management."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from pyfirmata import Arduino, util

if TYPE_CHECKING:
    from pyfirmata import Pin

    from mechatronics3.config import PinMap


class RobotBoard:
    """Manage an Arduino board connection, iterator, and pin acquisition.

    Usage as a context manager ensures the board is properly shut down::

        with RobotBoard(port="/dev/ttyUSB0") as rb:
            rb.motor_left_fwd.write(1)
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 57600) -> None:
        self._board = Arduino(port, baudrate=baudrate)
        self._iterator = util.Iterator(self._board)
        self._iterator.start()
        self._board.analog[0].enable_reporting()
        self._pins: dict[str, Pin] = {}

    # ------------------------------------------------------------------
    # Pin helpers
    # ------------------------------------------------------------------

    def digital_output(self, pin_number: int) -> Pin:
        """Return a digital output pin, caching repeated calls."""
        key = f"d:{pin_number}:o"
        if key not in self._pins:
            self._pins[key] = self._board.get_pin(key)
        return self._pins[key]

    def servo_pin(self, pin_number: int) -> Pin:
        """Return a servo pin, caching repeated calls."""
        key = f"d:{pin_number}:s"
        if key not in self._pins:
            self._pins[key] = self._board.get_pin(key)
        return self._pins[key]

    def analog_read(self, channel: int = 0) -> float | None:
        """Read the current value of an analog channel."""
        return self._board.analog[channel].read()

    # ------------------------------------------------------------------
    # Convenience: acquire all pins from a PinMap at once
    # ------------------------------------------------------------------

    def setup_pins(self, pins: PinMap) -> None:
        """Pre-acquire every pin listed in *pins* so they are cached."""
        self.digital_output(pins.motor_left_fwd)
        self.digital_output(pins.motor_left_bwd)
        self.digital_output(pins.motor_right_fwd)
        self.digital_output(pins.motor_right_bwd)
        self.digital_output(pins.echo)
        self.servo_pin(pins.servo_horizontal)
        self.servo_pin(pins.servo_vertical)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Arduino:
        """Access the underlying ``pyfirmata.Arduino`` instance."""
        return self._board

    def exit(self) -> None:
        """Safely shut down the board connection."""
        self._board.exit()

    def __enter__(self) -> RobotBoard:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exit()
