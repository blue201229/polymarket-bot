"""Redis client for caching and pub/sub."""
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


class Cache:
    """Simple typed cache wrapper around Redis."""

    def __init__(self, prefix: str, default_ttl: int = 300):
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        redis = await get_redis()
        value = await redis.get(self._key(key))
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        redis = await get_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await redis.set(self._key(key), serialized, ex=ttl or self.default_ttl)

    async def delete(self, key: str) -> None:
        redis = await get_redis()
        await redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(self._key(key)))


class PubSub:
    """Pub/sub wrapper for real-time event distribution to frontends."""

    CHANNELS = {
        "market_update": "polymarket:market:updates",
        "trade_executed": "polymarket:trades:executed",
        "ai_signal": "polymarket:ai:signals",
        "risk_alert": "polymarket:risk:alerts",
        "wallet_event": "polymarket:wallet:events",
        "anomaly": "polymarket:anomalies",
    }

    async def publish(self, channel: str, message: Any) -> None:
        redis = await get_redis()
        channel_key = self.CHANNELS.get(channel, channel)
        payload = json.dumps(message) if not isinstance(message, str) else message
        await redis.publish(channel_key, payload)

    async def subscribe(self, channel: str):
        redis = await get_redis()
        channel_key = self.CHANNELS.get(channel, channel)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel_key)
        return pubsub


pubsub = PubSub()
