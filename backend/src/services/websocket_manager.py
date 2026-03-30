from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Coroutine, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from backend.src.config import settings
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger

logger = get_logger("services.websocket")

MessageHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class WebSocketManager:
    """
    Manages WebSocket connections to Polymarket for real-time market data.

    Features:
    - Auto-reconnect with exponential backoff
    - Multiple subscription channels
    - Message routing to registered handlers
    - Health monitoring
    """

    def __init__(self) -> None:
        self._ws: Optional[Any] = None
        self._running = False
        self._subscriptions: dict[str, set[str]] = {}
        self._handlers: list[MessageHandler] = []
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._message_count = 0
        self._url = settings.polymarket_ws_url

    def register_handler(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    async def connect(self) -> None:
        self._running = True
        while self._running:
            try:
                logger.info("Connecting to WebSocket", url=self._url)
                async with websockets.connect(
                    self._url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0
                    logger.info("WebSocket connected")

                    await self._resubscribe()
                    await self._listen(ws)

            except ConnectionClosed as e:
                logger.warning("WebSocket connection closed", code=e.code, reason=str(e.reason))
            except Exception as e:
                logger.error("WebSocket error", error=str(e))

            if self._running:
                logger.info("Reconnecting in %ss", self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

    async def _listen(self, ws: Any) -> None:
        async for message in ws:
            try:
                data = json.loads(message)
                self._message_count += 1
                await self._dispatch(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WebSocket")
            except Exception as e:
                logger.error("Error processing WebSocket message", error=str(e))

    async def _dispatch(self, data: dict[str, Any]) -> None:
        for handler in self._handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error("Handler error", error=str(e))

    async def subscribe(self, channel: str, assets: list[str]) -> None:
        self._subscriptions.setdefault(channel, set()).update(assets)
        if self._ws:
            msg = {
                "type": "subscribe",
                "channel": channel,
                "assets_ids": assets,
            }
            await self._ws.send(json.dumps(msg))
            logger.info("Subscribed", channel=channel, assets=len(assets))

    async def unsubscribe(self, channel: str, assets: list[str]) -> None:
        if channel in self._subscriptions:
            self._subscriptions[channel] -= set(assets)
        if self._ws:
            msg = {
                "type": "unsubscribe",
                "channel": channel,
                "assets_ids": assets,
            }
            await self._ws.send(json.dumps(msg))

    async def _resubscribe(self) -> None:
        for channel, assets in self._subscriptions.items():
            if assets:
                await self.subscribe(channel, list(assets))

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("WebSocket disconnected", total_messages=self._message_count)

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._ws.open

    @property
    def message_count(self) -> int:
        return self._message_count
