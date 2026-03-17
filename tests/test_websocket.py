"""WebSocket endpoint tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from mechatronics3.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def app():
    mock_motor = MagicMock()
    mock_servo = MagicMock()

    from mechatronics3.server.app import create_app

    application = create_app()
    application.state.board = MagicMock()
    application.state.motor = mock_motor
    application.state.servo = mock_servo
    application.state.sensor = MagicMock()
    application.state.color_detector = MagicMock()
    application.state.ml_detector = MagicMock()
    application.state.upload_dir = None
    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestWebSocketConnect:
    def test_connect_and_receive_welcome(self, client: TestClient) -> None:
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "welcome"


class TestWebSocketMotor:
    def test_motor_command(self, client: TestClient, app) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text(json.dumps({"type": "motor", "payload": {"action": "forward", "duration": 0.5}}))
            ack = ws.receive_json()
            assert ack["type"] == "motor_ack"
            assert ack["payload"]["action"] == "forward"
        app.state.motor.forward.assert_called_once_with(0.5)

    def test_motor_rotate(self, client: TestClient, app) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text(json.dumps({"type": "motor", "payload": {"action": "rotate", "angle": 45}}))
            ack = ws.receive_json()
            assert ack["type"] == "motor_ack"
        app.state.motor.rotate.assert_called_once()


class TestWebSocketServo:
    def test_servo_command(self, client: TestClient, app) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text(json.dumps({"type": "servo", "payload": {"axis": "horizontal", "angle": 90}}))
            ack = ws.receive_json()
            assert ack["type"] == "servo_ack"
        app.state.servo.write_horizontal.assert_called_once_with(90.0)


class TestWebSocketSubscribe:
    def test_subscribe(self, client: TestClient) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text(json.dumps({"type": "subscribe", "payload": {"channels": ["sensor"]}}))
            ack = ws.receive_json()
            assert ack["type"] == "subscribed"
            assert "sensor" in ack["payload"]["channels"]


class TestWebSocketErrors:
    def test_invalid_json(self, client: TestClient) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text("not valid json{{{")
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "Invalid JSON" in err["payload"]["detail"]

    def test_unknown_type(self, client: TestClient) -> None:
        with client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()
            ws.send_text(json.dumps({"type": "bogus", "payload": {}}))
            err = ws.receive_json()
            assert err["type"] == "error"
