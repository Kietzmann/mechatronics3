"""OpenCV HSV colour detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from mechatronics3.config import HSVRange


@dataclass
class ColorMatch:
    """Centroid and mask from a single colour detection."""

    x: int
    y: int
    mask: NDArray[np.uint8]


class ColorDetector:
    """Detect colour blobs in video frames using HSV thresholding.

    Applies :func:`cv2.inRange` to an HSV-converted frame, then computes
    image moments to locate the centroid of the matching region.

    Parameters
    ----------
    camera_index:
        OpenCV :class:`~cv2.VideoCapture` device index.
    """

    def __init__(self, camera_index: int = 0) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._camera_index = camera_index

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open the camera capture device."""
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._camera_index)

    def close(self) -> None:
        """Release the camera and destroy any OpenCV windows."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        cv2.destroyAllWindows()

    def __enter__(self) -> ColorDetector:
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def read_frame(self) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
        """Capture a single frame and return ``(bgr, hsv)`` arrays.

        Raises
        ------
        RuntimeError
            If the camera is not open or the read fails.
        """
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError("Camera is not open — call open() or use as a context manager.")
        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise RuntimeError("Failed to capture frame from camera.")
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return frame, hsv

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_color(
        hsv_frame: NDArray[np.uint8],
        h_min: int,
        s_min: int,
        v_min: int,
        h_max: int,
        s_max: int,
        v_max: int,
    ) -> ColorMatch | None:
        """Find the centroid of a colour region in *hsv_frame*.

        Returns a :class:`ColorMatch` with the centroid coordinates and binary
        mask, or ``None`` if no pixels fall within the given HSV range.
        """
        lower = np.array((h_min, s_min, v_min), dtype=np.uint8)
        upper = np.array((h_max, s_max, v_max), dtype=np.uint8)
        mask: NDArray[np.uint8] = cv2.inRange(hsv_frame, lower, upper)

        moments = cv2.moments(mask, True)
        area = moments["m00"]
        if area == 0:
            return None

        cx = int(moments["m10"] / area)
        cy = int(moments["m01"] / area)
        return ColorMatch(x=cx, y=cy, mask=mask)

    def detect(self, hsv_range: HSVRange) -> ColorMatch | None:
        """Capture a frame and run colour detection for a single HSV range.

        Combines :meth:`read_frame` and :meth:`detect_color` in one call.
        """
        _bgr, hsv = self.read_frame()
        return self.detect_color(
            hsv,
            h_min=hsv_range.h_min,
            s_min=hsv_range.s_min,
            v_min=hsv_range.v_min,
            h_max=hsv_range.h_max,
            s_max=hsv_range.s_max,
            v_max=hsv_range.v_max,
        )

    def detect_multi(self, *ranges: HSVRange) -> list[ColorMatch | None]:
        """Capture one frame and detect multiple colours.

        Returns a list of :class:`ColorMatch` (or ``None``) matching the order
        of the supplied *ranges*.
        """
        _bgr, hsv = self.read_frame()
        return [
            self.detect_color(
                hsv,
                h_min=r.h_min,
                s_min=r.s_min,
                v_min=r.v_min,
                h_max=r.h_max,
                s_max=r.s_max,
                v_max=r.v_max,
            )
            for r in ranges
        ]
