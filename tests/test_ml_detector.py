"""Tests for CubeDetector — training and prediction with synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from mechatronics3.config import MLConfig
from mechatronics3.core.sensor import Scan3DResult
from mechatronics3.detection.ml_detector import CubeDetector, TrainResult


@pytest.fixture()
def training_data():
    """Synthetic dataset: vectors of 20 binary features with a clear signal.

    Label 1 = most features are 1; label 0 = most features are 0.
    """
    rng = np.random.RandomState(42)
    n_samples = 200
    n_features = 20

    x_pos = rng.binomial(1, 0.8, size=(n_samples // 2, n_features))
    x_neg = rng.binomial(1, 0.2, size=(n_samples // 2, n_features))

    x = np.vstack([x_pos, x_neg])
    y = np.array([1] * (n_samples // 2) + [0] * (n_samples // 2))
    return x, y


class TestInit:
    def test_default_parameters(self) -> None:
        det = CubeDetector()
        assert not det.is_fitted

    def test_from_config(self) -> None:
        cfg = MLConfig(n_estimators=5, learning_rate=0.05, max_depth=2)
        det = CubeDetector.from_config(cfg)
        assert not det.is_fitted


class TestFit:
    def test_fit_returns_train_result(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=5)
        result = det.fit(x, y, test_size=0.2, cv_folds=3)

        assert isinstance(result, TrainResult)
        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.cross_val_mean <= 1.0
        assert len(result.cross_val_scores) == 3
        assert det.is_fitted

    def test_high_accuracy_on_separable_data(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=10)
        result = det.fit(x, y, test_size=0.2, cv_folds=3)
        assert result.accuracy >= 0.8


class TestPredict:
    def test_predict_raises_before_fit(self) -> None:
        det = CubeDetector()
        with pytest.raises(RuntimeError, match="not been fitted"):
            det.predict([0] * 20)

    def test_predict_returns_bool(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=5)
        det.fit(x, y, test_size=0.1, cv_folds=3)

        result = det.predict([1] * 20)
        assert isinstance(result, bool)

    def test_predict_positive_vector(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=10)
        det.fit(x, y, test_size=0.1, cv_folds=3)
        assert det.predict([1] * 20) is True

    def test_predict_negative_vector(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=10)
        det.fit(x, y, test_size=0.1, cv_folds=3)
        assert det.predict([0] * 20) is False


class TestPredictFromScan:
    def test_predict_from_scan(self, training_data) -> None:
        x, y = training_data
        det = CubeDetector(n_estimators=5)
        det.fit(x, y, test_size=0.1, cv_folds=3)

        scan = Scan3DResult(
            horizontal=[0.0] * 20,
            vertical=[90.0] * 20,
            detections=[1] * 20,
        )
        result = det.predict_from_scan(scan)
        assert isinstance(result, bool)
