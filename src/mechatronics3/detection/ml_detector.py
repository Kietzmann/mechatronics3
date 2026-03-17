"""GradientBoosting-based cube detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import ArrayLike
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, train_test_split

if TYPE_CHECKING:
    from mechatronics3.config import MLConfig
    from mechatronics3.core.sensor import Scan3DResult


@dataclass
class TrainResult:
    """Metrics returned after a :meth:`CubeDetector.fit` call."""

    accuracy: float
    cross_val_scores: np.ndarray
    cross_val_mean: float


class CubeDetector:
    """Classify 3-D ultrasonic scans as *object present* or *empty*.

    Wraps a :class:`~sklearn.ensemble.GradientBoostingClassifier` trained on
    flattened binary detection vectors produced by
    :meth:`~mechatronics3.core.sensor.UltrasonicSensor.scan_3d`.

    Parameters
    ----------
    n_estimators:
        Number of boosting stages.
    learning_rate:
        Shrinks the contribution of each tree.
    max_depth:
        Maximum depth of the individual regression estimators.
    """

    def __init__(
        self,
        *,
        n_estimators: int = 10,
        learning_rate: float = 0.1,
        max_depth: int = 3,
    ) -> None:
        self._model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
        )
        self._is_fitted = False

    @classmethod
    def from_config(cls, config: MLConfig) -> CubeDetector:
        """Construct a detector from a :class:`~mechatronics3.config.MLConfig`."""
        return cls(
            n_estimators=config.n_estimators,
            learning_rate=config.learning_rate,
            max_depth=config.max_depth,
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        x: ArrayLike,
        y: ArrayLike,
        *,
        test_size: float = 0.1,
        cv_folds: int = 9,
    ) -> TrainResult:
        """Train the classifier and return evaluation metrics.

        Parameters
        ----------
        x:
            Feature matrix ``(n_samples, n_features)``.  Each row is a binary
            detection vector from a 3-D scan.
        y:
            Labels — ``1`` for *object present*, ``0`` otherwise.
        test_size:
            Fraction of data held out for test-set accuracy.
        cv_folds:
            Number of cross-validation folds.
        """
        x_arr = np.asarray(x)
        y_arr = np.asarray(y)

        x_train, x_test, y_train, y_test = train_test_split(x_arr, y_arr, test_size=test_size)
        self._model.fit(x_train, y_train)
        self._is_fitted = True

        accuracy = float(self._model.score(x_test, y_test))
        cv_scores = cross_val_score(self._model, x_arr, y_arr, cv=cv_folds)

        return TrainResult(
            accuracy=accuracy,
            cross_val_scores=cv_scores,
            cross_val_mean=float(cv_scores.mean()),
        )

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, detections: list[int]) -> bool:
        """Return ``True`` if the detection vector indicates an object.

        Parameters
        ----------
        detections:
            Flat list of binary flags, typically
            :attr:`~mechatronics3.core.sensor.Scan3DResult.detections`.

        Raises
        ------
        RuntimeError
            If the model has not been fitted yet.
        """
        if not self._is_fitted:
            raise RuntimeError("Model has not been fitted yet — call fit() first.")
        arr = np.asarray(detections).reshape(1, -1)
        return bool(self._model.predict(arr)[0])

    def predict_from_scan(self, scan: Scan3DResult) -> bool:
        """Convenience wrapper that accepts a :class:`Scan3DResult` directly."""
        return self.predict(scan.detections)

    @property
    def is_fitted(self) -> bool:
        """Whether the model has been trained."""
        return self._is_fitted
