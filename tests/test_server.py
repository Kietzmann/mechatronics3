"""FastAPI TestClient tests for all server endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from mechatronics3.config import get_settings
from mechatronics3.detection.color_detector import ColorMatch
from mechatronics3.detection.ml_detector import CubeDetector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def app(tmp_path):
    """Build a FastAPI app with mocked hardware components."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    mock_motor = MagicMock()
    mock_servo = MagicMock()
    mock_servo.read_horizontal.return_value = 65.0
    mock_servo.read_vertical.return_value = 90.0

    mock_sensor = MagicMock()
    mock_sensor.ping.return_value = 25.0

    mock_scan = MagicMock()
    mock_scan.angles = [0.0, 13.0, 26.0]
    mock_scan.distances = [30.0, 25.0, 40.0]
    mock_sensor.scan.return_value = mock_scan

    mock_scan3d = MagicMock()
    mock_scan3d.horizontal = [0.0, 13.0]
    mock_scan3d.vertical = [90.0, 90.0]
    mock_scan3d.detections = [1, 0]
    mock_sensor.scan_3d.return_value = mock_scan3d

    mock_color = MagicMock()
    mock_color.detect.return_value = ColorMatch(x=50, y=60, mask=np.zeros((10, 10), dtype=np.uint8))

    ml_detector = CubeDetector(n_estimators=5)

    from mechatronics3.server.app import create_app

    application = create_app()

    application.state.board = MagicMock()
    application.state.motor = mock_motor
    application.state.servo = mock_servo
    application.state.sensor = mock_sensor
    application.state.color_detector = mock_color
    application.state.ml_detector = ml_detector
    application.state.upload_dir = upload_dir

    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_header():
    return {"Authorization": "Bearer changeme"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAuth:
    def test_missing_token_returns_401_or_403(self, client: TestClient) -> None:
        resp = client.post("/api/robot/motor/stop", json={"duration": 0})
        assert resp.status_code in (401, 403)

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/robot/motor/stop",
            json={"duration": 0},
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_valid_token_accepted(self, client: TestClient, auth_header) -> None:
        resp = client.post("/api/robot/motor/stop", json={"duration": 0}, headers=auth_header)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Motor endpoints
# ---------------------------------------------------------------------------


class TestMotorEndpoints:
    def test_stop(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/motor/stop", json={"duration": 0.5}, headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["action"] == "stop"
        app.state.motor.stop.assert_called_once_with(0.5)

    def test_forward(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/motor/forward", json={"duration": 1.0}, headers=auth_header)
        assert resp.status_code == 200
        app.state.motor.forward.assert_called_once_with(1.0)

    def test_backward(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/motor/backward", json={"duration": 0.5}, headers=auth_header)
        assert resp.status_code == 200
        app.state.motor.backward.assert_called_once_with(0.5)

    def test_left_forward(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/motor/left_forward", json={"duration": 0.5}, headers=auth_header)
        assert resp.status_code == 200
        app.state.motor.left_forward.assert_called_once_with(0.5)

    def test_rotate(self, client: TestClient, auth_header, app) -> None:
        resp = client.post(
            "/api/robot/motor/rotate",
            json={"angle": 45.0, "angle_range": 130.0},
            headers=auth_header,
        )
        assert resp.status_code == 200
        app.state.motor.rotate.assert_called_once_with(45.0, 130.0)

    def test_rotate_missing_angle(self, client: TestClient, auth_header) -> None:
        resp = client.post("/api/robot/motor/rotate", json={"duration": 1.0}, headers=auth_header)
        assert resp.status_code == 422

    def test_unknown_action(self, client: TestClient, auth_header) -> None:
        resp = client.post("/api/robot/motor/nosuchaction", json={"duration": 1.0}, headers=auth_header)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Servo endpoints
# ---------------------------------------------------------------------------


class TestServoEndpoints:
    def test_set_horizontal(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/servo/horizontal", json={"angle": 90.0}, headers=auth_header)
        assert resp.status_code == 200
        app.state.servo.write_horizontal.assert_called_once_with(90.0)

    def test_set_vertical(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/servo/vertical", json={"angle": 45.0}, headers=auth_header)
        assert resp.status_code == 200
        app.state.servo.write_vertical.assert_called_once_with(45.0)

    def test_center(self, client: TestClient, auth_header, app) -> None:
        resp = client.post("/api/robot/servo/center", headers=auth_header)
        assert resp.status_code == 200
        app.state.servo.center.assert_called_once()

    def test_read_positions(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/robot/servo", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizontal"] == 65.0
        assert data["vertical"] == 90.0


# ---------------------------------------------------------------------------
# Sensor endpoints
# ---------------------------------------------------------------------------


class TestSensorEndpoints:
    def test_ping(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/robot/sensor/ping", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["distance_cm"] == 25.0

    def test_scan(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/robot/sensor/scan", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["angles"] == [0.0, 13.0, 26.0]
        assert data["distances"] == [30.0, 25.0, 40.0]

    def test_scan3d(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/robot/sensor/scan3d", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["detections"] == [1, 0]


# ---------------------------------------------------------------------------
# Colour detection endpoints
# ---------------------------------------------------------------------------


class TestColorDetectionEndpoints:
    def test_detect_color_default(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/detection/color", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected"] is True
        assert data["x"] == 50
        assert data["y"] == 60

    def test_detect_color_no_match(self, client: TestClient, auth_header, app) -> None:
        app.state.color_detector.detect.return_value = None
        resp = client.get("/api/detection/color", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["detected"] is False


# ---------------------------------------------------------------------------
# ML detection endpoints
# ---------------------------------------------------------------------------


class TestMLDetectionEndpoints:
    def test_status_not_fitted(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/detection/ml/status", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["is_fitted"] is False

    def test_predict_before_fit_returns_400(self, client: TestClient, auth_header) -> None:
        resp = client.post(
            "/api/detection/ml/predict",
            json={"detections": [0] * 20},
            headers=auth_header,
        )
        assert resp.status_code == 400

    def test_train_and_predict(self, client: TestClient, auth_header) -> None:
        rng = np.random.RandomState(0)
        x_pos = rng.binomial(1, 0.8, size=(50, 20)).tolist()
        x_neg = rng.binomial(1, 0.2, size=(50, 20)).tolist()
        x = x_pos + x_neg
        y = [1] * 50 + [0] * 50

        train_resp = client.post(
            "/api/detection/ml/train",
            json={"x": x, "y": y, "test_size": 0.1, "cv_folds": 3},
            headers=auth_header,
        )
        assert train_resp.status_code == 200
        train_data = train_resp.json()
        assert 0.0 <= train_data["accuracy"] <= 1.0
        assert len(train_data["cross_val_scores"]) == 3

        predict_resp = client.post(
            "/api/detection/ml/predict",
            json={"detections": [1] * 20},
            headers=auth_header,
        )
        assert predict_resp.status_code == 200
        assert isinstance(predict_resp.json()["object_detected"], bool)

        status_resp = client.get("/api/detection/ml/status", headers=auth_header)
        assert status_resp.json()["is_fitted"] is True


# ---------------------------------------------------------------------------
# Files endpoints
# ---------------------------------------------------------------------------


class TestFilesEndpoints:
    def test_list_empty(self, client: TestClient, auth_header) -> None:
        resp = client.get("/api/files/", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_upload_and_list(self, client: TestClient, auth_header) -> None:
        resp = client.post(
            "/api/files/upload",
            files={"file": ("hello.py", b"print('hello')", "text/x-python")},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "hello.py"

        listed = client.get("/api/files/", headers=auth_header).json()
        assert any(f["name"] == "hello.py" for f in listed)

    def test_upload_non_python_rejected(self, client: TestClient, auth_header) -> None:
        resp = client.post(
            "/api/files/upload",
            files={"file": ("bad.txt", b"data", "text/plain")},
            headers=auth_header,
        )
        assert resp.status_code == 422

    def test_execute_script(self, client: TestClient, auth_header, app) -> None:
        upload_dir: Path = app.state.upload_dir
        script = upload_dir / "test_run.py"
        script.write_text("print('executed')")

        resp = client.post(
            "/api/files/execute",
            json={"filename": "test_run.py", "timeout": 10},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exit_code"] == 0
        assert "executed" in data["stdout"]

    def test_execute_nonexistent(self, client: TestClient, auth_header) -> None:
        resp = client.post(
            "/api/files/execute",
            json={"filename": "missing.py"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    def test_delete_file(self, client: TestClient, auth_header, app) -> None:
        upload_dir: Path = app.state.upload_dir
        script = upload_dir / "deleteme.py"
        script.write_text("pass")

        resp = client.delete("/api/files/deleteme.py", headers=auth_header)
        assert resp.status_code == 200
        assert not script.exists()

    def test_delete_nonexistent(self, client: TestClient, auth_header) -> None:
        resp = client.delete("/api/files/ghost.py", headers=auth_header)
        assert resp.status_code == 404

    def test_path_traversal_rejected(self, client: TestClient, auth_header) -> None:
        resp = client.post(
            "/api/files/upload",
            files={"file": ("../escape.py", b"bad", "text/x-python")},
            headers=auth_header,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_index_returns_html(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
