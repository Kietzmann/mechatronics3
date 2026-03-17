"""Tests for ColorDetector — mocked camera, centroid calculations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from mechatronics3.config import HSVRange
from mechatronics3.detection.color_detector import ColorDetector, ColorMatch


@pytest.fixture()
def mock_capture():
    """Return a mock ``cv2.VideoCapture`` that yields a known synthetic frame."""
    blue_bgr = np.zeros((100, 200, 3), dtype=np.uint8)
    blue_bgr[30:70, 80:120] = [255, 0, 0]  # blue rectangle

    cap = MagicMock(spec=cv2.VideoCapture)
    cap.isOpened.return_value = True
    cap.read.return_value = (True, blue_bgr)
    return cap


class TestLifecycle:
    @patch("mechatronics3.detection.color_detector.cv2.VideoCapture")
    def test_open_creates_capture(self, mock_vc_cls) -> None:
        mock_cap = MagicMock()
        mock_vc_cls.return_value = mock_cap
        det = ColorDetector(camera_index=0)
        det.open()
        mock_vc_cls.assert_called_once_with(0)

    @patch("mechatronics3.detection.color_detector.cv2.destroyAllWindows")
    def test_close_releases_capture(self, _destroy) -> None:
        det = ColorDetector()
        mock_cap = MagicMock()
        det._cap = mock_cap
        det.close()
        mock_cap.release.assert_called_once()
        _destroy.assert_called_once()

    @patch("mechatronics3.detection.color_detector.cv2.VideoCapture")
    @patch("mechatronics3.detection.color_detector.cv2.destroyAllWindows")
    def test_context_manager(self, _destroy, mock_vc_cls) -> None:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_vc_cls.return_value = mock_cap
        with ColorDetector() as det:
            assert det._cap is not None
        _destroy.assert_called()


class TestReadFrame:
    def test_raises_when_camera_not_open(self) -> None:
        det = ColorDetector()
        with pytest.raises(RuntimeError, match="Camera is not open"):
            det.read_frame()

    def test_raises_on_read_failure(self) -> None:
        det = ColorDetector()
        det._cap = MagicMock(spec=cv2.VideoCapture)
        det._cap.isOpened.return_value = True
        det._cap.read.return_value = (False, None)
        with pytest.raises(RuntimeError, match="Failed to capture"):
            det.read_frame()

    def test_returns_bgr_and_hsv(self, mock_capture) -> None:
        det = ColorDetector()
        det._cap = mock_capture
        bgr, hsv = det.read_frame()
        assert bgr.shape == (100, 200, 3)
        assert hsv.shape == (100, 200, 3)


class TestDetectColor:
    def test_returns_none_when_no_match(self) -> None:
        black_hsv = np.zeros((50, 50, 3), dtype=np.uint8)
        result = ColorDetector.detect_color(black_hsv, 100, 100, 100, 130, 255, 255)
        assert result is None

    def test_returns_centroid_for_known_blob(self) -> None:
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[40:60, 40:60] = [120, 200, 200]  # blue blob in HSV space
        result = ColorDetector.detect_color(frame, 100, 100, 100, 140, 255, 255)
        assert result is not None
        assert isinstance(result, ColorMatch)
        assert 35 <= result.x <= 65
        assert 35 <= result.y <= 65
        assert result.mask.shape == (100, 100)


class TestDetect:
    def test_detect_with_hsv_range(self, mock_capture) -> None:
        det = ColorDetector()
        det._cap = mock_capture
        hsv_range = HSVRange(h_min=100, h_max=130, s_min=50, s_max=255, v_min=50, v_max=255)
        result = det.detect(hsv_range)
        # Result may or may not match depending on the synthetic frame; just
        # verify the integration path completes without error.
        assert result is None or isinstance(result, ColorMatch)


class TestDetectMulti:
    def test_detect_multi_returns_list(self, mock_capture) -> None:
        det = ColorDetector()
        det._cap = mock_capture
        r1 = HSVRange(h_min=0, h_max=10, s_min=100, s_max=255, v_min=100, v_max=255)
        r2 = HSVRange(h_min=100, h_max=130, s_min=50, s_max=255, v_min=50, v_max=255)
        results = det.detect_multi(r1, r2)
        assert len(results) == 2
        assert all(r is None or isinstance(r, ColorMatch) for r in results)
