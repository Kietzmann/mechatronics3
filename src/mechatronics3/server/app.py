"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from mechatronics3.config import get_settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


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

    yield

    if color_detector is not None:
        color_detector.close()
    if board is not None:
        board.exit()
        logger.info("Hardware disconnected")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="Mechatronics3",
        description="REST API for Arduino-based mobile robot control",
        version="0.1.0",
        lifespan=_lifespan,
    )

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

    from mechatronics3.server.routes import detection_router, files_router, robot_router

    app.include_router(robot_router, prefix="/api/robot", tags=["robot"])
    app.include_router(detection_router, prefix="/api/detection", tags=["detection"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request})

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
