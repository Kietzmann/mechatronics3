"""WebSocket endpoint for real-time robot control and telemetry."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

_subscribers: dict[WebSocket, set[str]] = {}


async def broadcast(channel: str, payload: dict[str, Any]) -> None:
    """Push a message to all clients subscribed to *channel*."""
    msg = json.dumps({"type": channel, "payload": payload})
    stale: list[WebSocket] = []
    for ws, channels in _subscribers.items():
        if channel in channels:
            try:
                await ws.send_text(msg)
            except Exception:
                stale.append(ws)
    for ws in stale:
        _subscribers.pop(ws, None)


async def _handle_motor(ws: WebSocket, payload: dict[str, Any]) -> None:
    motor = getattr(ws.app.state, "motor", None)
    if motor is None:
        await ws.send_json({"type": "error", "payload": {"detail": "Motor unavailable"}})
        return
    action = payload.get("action", "stop")
    duration = float(payload.get("duration", 1.0))
    if action == "rotate":
        angle = float(payload.get("angle", 65.0))
        angle_range = float(payload.get("angle_range", 130.0))
        await asyncio.to_thread(motor.rotate, angle, angle_range)
    else:
        fn = getattr(motor, action, None)
        if fn is None:
            await ws.send_json({"type": "error", "payload": {"detail": f"Unknown action: {action}"}})
            return
        await asyncio.to_thread(fn, duration)
    await ws.send_json({"type": "motor_ack", "payload": {"action": action}})


async def _handle_servo(ws: WebSocket, payload: dict[str, Any]) -> None:
    servo = getattr(ws.app.state, "servo", None)
    if servo is None:
        await ws.send_json({"type": "error", "payload": {"detail": "Servo unavailable"}})
        return
    axis = payload.get("axis", "horizontal")
    angle = float(payload.get("angle", 90.0))
    if axis == "horizontal":
        await asyncio.to_thread(servo.write_horizontal, angle)
    else:
        await asyncio.to_thread(servo.write_vertical, angle)
    await ws.send_json({"type": "servo_ack", "payload": {"axis": axis, "angle": angle}})


async def _handle_subscribe(ws: WebSocket, payload: dict[str, Any]) -> None:
    channels = set(payload.get("channels", []))
    _subscribers[ws] = _subscribers.get(ws, set()) | channels
    await ws.send_json({"type": "subscribed", "payload": {"channels": sorted(_subscribers[ws])}})


_HANDLERS = {
    "motor": _handle_motor,
    "servo": _handle_servo,
    "subscribe": _handle_subscribe,
}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_json({"type": "welcome", "payload": {"message": "Connected to Mechatronics3 WS"}})
    _subscribers[ws] = set()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "payload": {"detail": "Invalid JSON"}})
                continue
            msg_type = msg.get("type", "")
            handler = _HANDLERS.get(msg_type)
            if handler is None:
                await ws.send_json({"type": "error", "payload": {"detail": f"Unknown type: {msg_type}"}})
                continue
            await handler(ws, msg.get("payload", {}))
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.pop(ws, None)
