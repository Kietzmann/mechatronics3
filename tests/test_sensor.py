"""Tests for UltrasonicSensor — mocked ping responses, scan structure."""

from __future__ import annotations

from unittest.mock import patch

from mechatronics3.core.sensor import Scan3DResult, ScanResult, UltrasonicSensor


class TestPing:
    @patch("mechatronics3.core.sensor.time.sleep")
    def test_ping_averages_samples(self, _sleep, sensor: UltrasonicSensor) -> None:
        distance = sensor.ping(samples=5)
        assert isinstance(distance, float)
        assert distance > 0

    @patch("mechatronics3.core.sensor.time.sleep")
    def test_ping_single_sample(self, _sleep, sensor: UltrasonicSensor) -> None:
        distance = sensor.ping(samples=1)
        assert isinstance(distance, float)


class TestScan:
    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_returns_scan_result(self, _sleep, sensor: UltrasonicSensor) -> None:
        result = sensor.scan(angle_min=0, angle_max=26, angle_step=13, samples=1)
        assert isinstance(result, ScanResult)
        assert result.angles == [0.0, 13.0, 26.0]
        assert len(result.distances) == 3

    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_empty_when_min_exceeds_max(self, _sleep, sensor: UltrasonicSensor) -> None:
        result = sensor.scan(angle_min=180, angle_max=0, angle_step=10)
        assert result.angles == []
        assert result.distances == []


class TestScan3D:
    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_3d_structure(self, _sleep, sensor: UltrasonicSensor) -> None:
        result = sensor.scan_3d(
            angle_min=0,
            angle_max=13,
            angle_step=13,
            vertical_angles=(90,),
            distance_threshold=40.0,
            samples=1,
        )
        assert isinstance(result, Scan3DResult)
        assert len(result.horizontal) == 2
        assert len(result.vertical) == 2
        assert len(result.detections) == 2
        assert all(isinstance(d, int) for d in result.detections)

    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_3d_close_objects_detected(self, _sleep, sensor: UltrasonicSensor) -> None:
        sensor._echo._ping_value = 100.0  # ~1.7 cm — below threshold
        result = sensor.scan_3d(
            angle_min=0,
            angle_max=0,
            angle_step=13,
            vertical_angles=(90,),
            distance_threshold=40.0,
            samples=1,
        )
        assert result.detections == [1]

    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_3d_far_objects_not_detected(self, _sleep, sensor: UltrasonicSensor) -> None:
        sensor._echo._ping_value = 10000.0  # ~172 cm — above threshold
        result = sensor.scan_3d(
            angle_min=0,
            angle_max=0,
            angle_step=13,
            vertical_angles=(90,),
            distance_threshold=40.0,
            samples=1,
        )
        assert result.detections == [0]

    @patch("mechatronics3.core.sensor.time.sleep")
    def test_scan_3d_zero_distance_not_flagged(self, _sleep, sensor: UltrasonicSensor) -> None:
        sensor._echo._ping_value = 0.0  # 0 cm — should not be flagged
        result = sensor.scan_3d(
            angle_min=0,
            angle_max=0,
            angle_step=13,
            vertical_angles=(90,),
            distance_threshold=40.0,
            samples=1,
        )
        assert result.detections == [0]
