"""Object-detection subsystem — ML and colour-based detectors."""

from mechatronics3.detection.color_detector import ColorDetector, ColorMatch
from mechatronics3.detection.ml_detector import CubeDetector, TrainResult

__all__ = ["ColorDetector", "ColorMatch", "CubeDetector", "TrainResult"]
