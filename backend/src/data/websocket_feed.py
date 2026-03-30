"""
WebSocket feed — live market data from Polymarket CLOB WebSocket API.

Handles:
- Connection management with reconnect logic
- Multi-market subscription
- Publishing price updates to Redis pub/sub
- Feeding real-time data to anomaly detector
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import pubsub, Cache
from src.ai.anomaly_detector import detect_market_anomalies, publish_anomalies

logger = get_logger(__name__)

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

_price_history_cache = Cache("ws:price_history", default_ttl=3600)
_spread_history_cache = Cache("ws:spread_history", default_ttl=3600)
_liquidity_history_cache = Cache("ws:liquidity_history", default_ttl=3600)


class MarketFeed:
    """
    Real-time WebSocket feed for Polymarket markets.

    Design:
    - Subscribes to a set of markets
    - Parses tick updates
    - Publishes to Redis for all connected frontends
    - Runs anomaly detection on each update
    """

    def __init__(self):
        self._subscribed: Set[str] = set()
        self._running = False
        self._ws = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._message_handlers: List[Callable] = []
        self._update_count = 0

    def add_handler(self, handler: Callable) -> None:
        """Register a callback for market updates."""
        self._message_handlers.append(handler)

    def subscribe(self, condition_ids: List[str]) -> None:
        """Add markets to subscription list."""
        self._subscribed.update(condition_ids)

    def unsubscribe(self, condition_ids: List[str]) -> None:
        """Remove markets from subscription list."""
        self._subscribed.difference_update(condition_ids)

    async def start(self) -> None:
        """Start the WebSocket feed with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                await self._connect_and_stream()
                self._reconnect_delay = 1.0  # Reset on clean disconnect
            except Exception as e:
                logger.warning("ws_feed_disconnected", error=str(e), retry_in=self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _connect_and_stream(self) -> None:
        logger.info("ws_feed_connecting", url=WS_URL, markets=len(self._subscribed))

        async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=10) as ws:
            self._ws = ws
            logger.info("ws_feed_connected")

            if self._subscribed:
                await self._subscribe_all(ws)

            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)

    async def _subscribe_all(self, ws) -> None:
        """Send subscription message for all tracked markets."""
        sub_message = {
            "auth": {},
            "markets": list(self._subscribed),
            "assets_ids": [],
            "type": "Market",
        }
        await ws.send(json.dumps(sub_message))
        logger.info("ws_feed_subscribed", count=len(self._subscribed))

    async def _handle_message(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        event_type = data.get("event_type")

        if event_type == "price_change":
            await self._handle_price_change(data)
        elif event_type == "book":
            await self._handle_book_update(data)
        elif event_type == "tick_size_change":
            pass  # Ignore
        else:
            logger.debug("ws_unknown_event", event_type=event_type)

    async def _handle_price_change(self, data: Dict[str, Any]) -> None:
        """Process a price change event."""
        condition_id = data.get("market", data.get("asset_id", ""))
        price = float(data.get("price", 0))
        outcome = data.get("outcome", "Yes")
        timestamp = datetime.now(timezone.utc).isoformat()

        update = {
            "condition_id": condition_id,
            "price": price,
            "outcome": outcome,
            "timestamp": timestamp,
            "type": "price_change",
        }

        # Update price history in cache (rolling window)
        history_key = f"{condition_id}:{outcome}"
        history = await _price_history_cache.get(history_key) or []
        history.append(price)
        if len(history) > 100:
            history = history[-100:]
        await _price_history_cache.set(history_key, history)

        # Publish to all frontends
        await pubsub.publish("market_update", update)
        self._update_count += 1

        # Run anomaly detection every 10 updates per market
        if self._update_count % 10 == 0:
            await self._run_anomaly_check(condition_id, data)

        # Notify handlers
        for handler in self._message_handlers:
            try:
                await handler(update)
            except Exception as e:
                logger.error("ws_handler_error", error=str(e))

    async def _handle_book_update(self, data: Dict[str, Any]) -> None:
        """Process orderbook update."""
        condition_id = data.get("market", "")
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if not bids or not asks:
            return

        best_bid = float(bids[0].get("price", 0)) if bids else 0
        best_ask = float(asks[0].get("price", 0)) if asks else 0
        spread_pct = (best_ask - best_bid) / best_ask if best_ask else 0

        # Track spread history
        spread_history = await _spread_history_cache.get(condition_id) or []
        spread_history.append(spread_pct)
        if len(spread_history) > 100:
            spread_history = spread_history[-100:]
        await _spread_history_cache.set(condition_id, spread_history)

        update = {
            "condition_id": condition_id,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": spread_pct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "book_update",
        }
        await pubsub.publish("market_update", update)

    async def _run_anomaly_check(self, condition_id: str, current_data: Dict[str, Any]) -> None:
        """Check for anomalies and publish if found."""
        spread_history = await _spread_history_cache.get(condition_id) or []
        price_history = await _price_history_cache.get(f"{condition_id}:Yes") or []
        liquidity_history = await _liquidity_history_cache.get(condition_id) or []

        anomalies = detect_market_anomalies(
            condition_id=condition_id,
            current_data={
                "spread_pct": current_data.get("spread_pct", 0),
                "liquidity": current_data.get("liquidity", 0),
            },
            historical_data={
                "spread_history": spread_history,
                "price_history": price_history,
                "liquidity_history": liquidity_history,
            },
        )

        if anomalies:
            await publish_anomalies(anomalies)


# Module-level singleton
_feed_instance: Optional[MarketFeed] = None


def get_market_feed() -> MarketFeed:
    global _feed_instance
    if _feed_instance is None:
        _feed_instance = MarketFeed()
    return _feed_instance
