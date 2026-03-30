"""
WebSocket endpoint — real-time market and trade updates to web/mobile clients.

Uses Redis pub/sub as the message bus, so all backend services
can publish events that get forwarded to connected clients.
"""
import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from src.core.logging import get_logger
from src.core.redis_client import get_redis

logger = get_logger(__name__)

CHANNELS = [
    "polymarket:market:updates",
    "polymarket:trades:executed",
    "polymarket:ai:signals",
    "polymarket:risk:alerts",
    "polymarket:anomalies",
]


class ConnectionManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("ws_client_connected", total=len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("ws_client_disconnected", total=len(self._connections))

    async def broadcast(self, message: str) -> None:
        dead = set()
        for ws in self._connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead


manager = ConnectionManager()


async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        # Start listening to Redis in the background
        listener_task = asyncio.create_task(_listen_redis(ws))

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # Handle client subscription preferences
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive
                await ws.send_text(json.dumps({"type": "keepalive"}))
            except WebSocketDisconnect:
                break

    finally:
        listener_task.cancel()
        manager.disconnect(ws)


async def _listen_redis(ws: WebSocket) -> None:
    """Subscribe to all Redis channels and forward to this WebSocket client."""
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(*CHANNELS)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            if ws.client_state != WebSocketState.CONNECTED:
                break
            await ws.send_text(message["data"])
    except Exception as e:
        logger.debug("ws_redis_listener_stopped", error=str(e))
    finally:
        await pubsub.unsubscribe(*CHANNELS)
        await pubsub.aclose()
