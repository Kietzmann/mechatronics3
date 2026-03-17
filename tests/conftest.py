"""Shared test fixtures and mock Arduino board."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mechatronics3.config import Settings

# ---------------------------------------------------------------------------
# Mock pyfirmata primitives
# ---------------------------------------------------------------------------


class MockPin:
    """Lightweight stand-in for a ``pyfirmata.Pin``."""

    def __init__(self) -> None:
        self._value: float | int | None = None
        self._ping_value: float = 500.0  # microseconds

    def write(self, value: float | int) -> None:
        self._value = value

    def read(self) -> float | int | None:
        return self._value

    def ping(self) -> float:
        return self._ping_value

    def enable_reporting(self) -> None:
        pass


class MockArduino:
    """Stand-in for ``pyfirmata.Arduino``."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._pins: dict[str, MockPin] = {}
        self.analog = [MockPin()]

    def get_pin(self, spec: str) -> MockPin:
        if spec not in self._pins:
            self._pins[spec] = MockPin()
        return self._pins[spec]

    def exit(self) -> None:
        pass


class MockIterator:
    """Stand-in for ``pyfirmata.util.Iterator``."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def start(self) -> None:
        pass


class _MockUtil:
    """Namespace mirroring ``pyfirmata.util`` for patching."""

    Iterator = MockIterator

    @staticmethod
    def ping_time_to_distance(us: float) -> float:
        return us / 29.0 / 2.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_pyfirmata():
    """Patch Arduino and util where they are imported inside core modules."""
    with (
        patch("mechatronics3.core.board.Arduino", MockArduino),
        patch("mechatronics3.core.board.util", _MockUtil),
        patch("mechatronics3.core.sensor.util", _MockUtil),
    ):
        yield


@pytest.fixture()
def board(mock_pyfirmata):
    """Return a :class:`RobotBoard` backed by mocked hardware."""
    from mechatronics3.core.board import RobotBoard

    return RobotBoard(port="/dev/null")


@pytest.fixture()
def motor(board):
    """Return a :class:`MotorController` wired to the mock board."""
    from mechatronics3.core.motor import MotorController

    return MotorController(board)


@pytest.fixture()
def servo(board):
    """Return a :class:`ServoController` wired to the mock board."""
    from mechatronics3.core.servo import ServoController

    return ServoController(board)


@pytest.fixture()
def sensor(board, servo):
    """Return an :class:`UltrasonicSensor` wired to the mock board."""
    from mechatronics3.core.sensor import UltrasonicSensor

    return UltrasonicSensor(board, servo)


@pytest.fixture()
def settings(monkeypatch, tmp_path):
    """Return a fresh :class:`Settings` with deterministic defaults.

    Clears the ``get_settings`` LRU cache so env-var overrides in
    individual tests are picked up.
    """
    from mechatronics3.config import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("MECH_AUTH_TOKEN", raising=False)
    return Settings()


@pytest.fixture()
def upload_dir(tmp_path) -> Path:
    d = tmp_path / "uploads"
    d.mkdir()
    return d
