"""REST endpoints for colour and ML detection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from mechatronics3.config import HSVRange, Settings, get_settings
from mechatronics3.server.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class ColorResponse(BaseModel):
    detected: bool
    x: int | None = None
    y: int | None = None


class TrainRequest(BaseModel):
    x: list[list[int]]
    y: list[int]
    test_size: float = 0.1
    cv_folds: int = 9


class TrainResponse(BaseModel):
    accuracy: float
    cross_val_mean: float
    cross_val_scores: list[float]


class PredictRequest(BaseModel):
    detections: list[int]


class PredictResponse(BaseModel):
    object_detected: bool


class MLStatusResponse(BaseModel):
    is_fitted: bool


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_color_detector(request: Request):
    detector = getattr(request.app.state, "color_detector", None)
    if detector is None:
        raise HTTPException(status_code=503, detail="Color detector unavailable — camera not connected")
    return detector


def _get_ml_detector(request: Request):
    detector = getattr(request.app.state, "ml_detector", None)
    if detector is None:
        raise HTTPException(status_code=503, detail="ML detector unavailable")
    return detector


# ---------------------------------------------------------------------------
# Colour detection
# ---------------------------------------------------------------------------


@router.get("/color", summary="Detect colour centroid in camera frame", response_model=ColorResponse)
def detect_color(
    h_min: Annotated[int | None, Query(ge=0, le=180)] = None,
    h_max: Annotated[int | None, Query(ge=0, le=180)] = None,
    s_min: Annotated[int | None, Query(ge=0, le=255)] = None,
    s_max: Annotated[int | None, Query(ge=0, le=255)] = None,
    v_min: Annotated[int | None, Query(ge=0, le=255)] = None,
    v_max: Annotated[int | None, Query(ge=0, le=255)] = None,
    detector=Depends(_get_color_detector),
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> ColorResponse:
    base = settings.hsv
    hsv = HSVRange(
        h_min=h_min if h_min is not None else base.h_min,
        h_max=h_max if h_max is not None else base.h_max,
        s_min=s_min if s_min is not None else base.s_min,
        s_max=s_max if s_max is not None else base.s_max,
        v_min=v_min if v_min is not None else base.v_min,
        v_max=v_max if v_max is not None else base.v_max,
    )
    match = detector.detect(hsv)
    if match is None:
        return ColorResponse(detected=False)
    return ColorResponse(detected=True, x=match.x, y=match.y)


# ---------------------------------------------------------------------------
# ML detection
# ---------------------------------------------------------------------------


@router.post("/ml/train", summary="Train the cube detector", response_model=TrainResponse)
def train_ml(
    body: TrainRequest,
    detector=Depends(_get_ml_detector),
) -> TrainResponse:
    result = detector.fit(body.x, body.y, test_size=body.test_size, cv_folds=body.cv_folds)
    return TrainResponse(
        accuracy=result.accuracy,
        cross_val_mean=result.cross_val_mean,
        cross_val_scores=result.cross_val_scores.tolist(),
    )


@router.post("/ml/predict", summary="Predict from a detection vector", response_model=PredictResponse)
def predict_ml(
    body: PredictRequest,
    detector=Depends(_get_ml_detector),
) -> PredictResponse:
    try:
        detected = detector.predict(body.detections)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PredictResponse(object_detected=detected)


@router.get("/ml/status", summary="Check if ML model is fitted", response_model=MLStatusResponse)
def ml_status(
    detector=Depends(_get_ml_detector),
) -> MLStatusResponse:
    return MLStatusResponse(is_fitted=detector.is_fitted)
