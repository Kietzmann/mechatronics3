"""Tests for Settings loading from defaults and environment variables."""

from __future__ import annotations

from mechatronics3.config import (
    HSVRange,
    MLConfig,
    PinMap,
    ScanConfig,
    Settings,
    get_settings,
)


class TestDefaults:
    def test_default_serial_port(self) -> None:
        s = Settings()
        assert s.serial_port == "/dev/ttyUSB0"

    def test_default_baud_rate(self) -> None:
        s = Settings()
        assert s.baud_rate == 57600

    def test_default_server(self) -> None:
        s = Settings()
        assert s.server_host == "0.0.0.0"
        assert s.server_port == 8000

    def test_default_auth_token(self) -> None:
        s = Settings()
        assert s.auth_token == "changeme"

    def test_default_pin_map(self) -> None:
        p = Settings().pins
        assert isinstance(p, PinMap)
        assert p.motor_left_fwd == 9
        assert p.motor_left_bwd == 8
        assert p.motor_right_fwd == 11
        assert p.motor_right_bwd == 10
        assert p.servo_horizontal == 5
        assert p.servo_vertical == 6
        assert p.echo == 7

    def test_default_hsv(self) -> None:
        h = Settings().hsv
        assert isinstance(h, HSVRange)
        assert h.h_min == 0 and h.h_max == 180

    def test_default_scan(self) -> None:
        sc = Settings().scan
        assert isinstance(sc, ScanConfig)
        assert sc.angle_step == 13

    def test_default_ml(self) -> None:
        ml = Settings().ml
        assert isinstance(ml, MLConfig)
        assert ml.n_estimators == 10


class TestEnvOverride:
    def test_serial_port_override(self, monkeypatch) -> None:
        monkeypatch.setenv("MECH_SERIAL_PORT", "COM3")
        s = Settings()
        assert s.serial_port == "COM3"

    def test_baud_rate_override(self, monkeypatch) -> None:
        monkeypatch.setenv("MECH_BAUD_RATE", "9600")
        s = Settings()
        assert s.baud_rate == 9600

    def test_server_port_override(self, monkeypatch) -> None:
        monkeypatch.setenv("MECH_SERVER_PORT", "3000")
        s = Settings()
        assert s.server_port == 3000

    def test_auth_token_override(self, monkeypatch) -> None:
        monkeypatch.setenv("MECH_AUTH_TOKEN", "supersecret")
        s = Settings()
        assert s.auth_token == "supersecret"

    def test_nested_pin_override(self, monkeypatch) -> None:
        monkeypatch.setenv("MECH_PINS__ECHO", "12")
        s = Settings()
        assert s.pins.echo == 12


class TestGetSettings:
    def test_singleton_caching(self) -> None:
        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_cache_clear_yields_new_instance(self) -> None:
        get_settings.cache_clear()
        a = get_settings()
        get_settings.cache_clear()
        b = get_settings()
        assert a is not b
