"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from mechatronics3.config import get_settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


async def _sensor_broadcast_loop(app: FastAPI, interval_ms: int) -> None:
    """Periodically ping the sensor and broadcast results via WebSocket."""
    from mechatronics3.server.routes.websocket import broadcast

    interval_s = interval_ms / 1000.0
    while True:
        await asyncio.sleep(interval_s)
        sensor = getattr(app.state, "sensor", None)
        if sensor is None:
            continue
        try:
            distance = await asyncio.to_thread(sensor.ping)
            await broadcast("sensor_data", {"distance_cm": distance})
        except Exception:
            logger.debug("Sensor broadcast tick failed", exc_info=True)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connect optional hardware on startup, tear down on shutdown."""
    settings = get_settings()

    board = motor = servo = sensor = None
    try:
        from mechatronics3.core import (
            MotorController,
            RobotBoard,
            ServoController,
            UltrasonicSensor,
        )

        board = RobotBoard(port=settings.serial_port, baudrate=settings.baud_rate)
        board.setup_pins(settings.pins)
        pins = settings.pins
        servo = ServoController(board, h_pin=pins.servo_horizontal, v_pin=pins.servo_vertical)
        motor = MotorController(
            board,
            lf_pin=pins.motor_left_fwd,
            lb_pin=pins.motor_left_bwd,
            rf_pin=pins.motor_right_fwd,
            rb_pin=pins.motor_right_bwd,
            motor_config=settings.motor,
        )
        sensor = UltrasonicSensor(board, servo, echo_pin=pins.echo)
        logger.info("Hardware connected on %s", settings.serial_port)
    except Exception:
        logger.warning("Hardware not available — robot endpoints will return 503", exc_info=True)

    color_detector = None
    try:
        from mechatronics3.detection import ColorDetector

        color_detector = ColorDetector(camera_index=settings.camera_index)
        color_detector.open()
        logger.info("Camera opened (index %d)", settings.camera_index)
    except Exception:
        logger.warning("Camera not available — colour detection will return 503", exc_info=True)

    ml_detector = None
    try:
        from mechatronics3.detection import CubeDetector

        ml_detector = CubeDetector.from_config(settings.ml)
    except Exception:
        logger.warning("ML detector could not be initialised", exc_info=True)

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    app.state.board = board
    app.state.motor = motor
    app.state.servo = servo
    app.state.sensor = sensor
    app.state.color_detector = color_detector
    app.state.ml_detector = ml_detector
    app.state.upload_dir = upload_dir

    broadcast_task = None
    if settings.scan.broadcast_interval_ms > 0:
        broadcast_task = asyncio.create_task(
            _sensor_broadcast_loop(app, settings.scan.broadcast_interval_ms),
        )

    yield

    if broadcast_task is not None:
        broadcast_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await broadcast_task

    if color_detector is not None:
        color_detector.close()
    if board is not None:
        board.exit()
        logger.info("Hardware disconnected")


class HealthResponse(BaseModel):
    board_connected: bool
    camera_open: bool
    ml_fitted: bool


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Mechatronics3",
        description="REST API for Arduino-based mobile robot control",
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

    from mechatronics3.server.routes import detection_router, files_router, robot_router, ws_router

    app.include_router(robot_router, prefix="/api/robot", tags=["robot"])
    app.include_router(detection_router, prefix="/api/detection", tags=["detection"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])
    app.include_router(ws_router)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    async def health(request: Request) -> HealthResponse:
        board = getattr(request.app.state, "board", None)
        camera = getattr(request.app.state, "color_detector", None)
        ml = getattr(request.app.state, "ml_detector", None)
        return HealthResponse(
            board_connected=board is not None,
            camera_open=camera is not None,
            ml_fitted=ml is not None and ml.is_fitted,
        )

    return app


def start() -> None:
    """Start the server with uvicorn (called from CLI)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "mechatronics3.server.app:create_app",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )
