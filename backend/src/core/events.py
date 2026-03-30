from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """In-process async event bus for decoupled component communication."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = [
            h for h in self._handlers[event_type] if h is not handler
        ]

    async def publish(self, event_type: str, **data: Any) -> None:
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return
        await asyncio.gather(
            *(h(**data) for h in handlers),
            return_exceptions=True,
        )


event_bus = EventBus()


class Events:
    MARKET_DISCOVERED = "market.discovered"
    MARKET_UPDATED = "market.updated"
    TRADE_SIGNAL = "trade.signal"
    TRADE_EXECUTED = "trade.executed"
    TRADE_CLOSED = "trade.closed"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    WALLET_ACTIVITY = "wallet.activity"
    ANOMALY_DETECTED = "anomaly.detected"
    AI_SCORE_UPDATED = "ai.score_updated"
    ALERT_CREATED = "alert.created"
    RISK_BREACH = "risk.breach"
