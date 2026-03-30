import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.config import settings


logger = logging.getLogger(__name__)


def _stable_key(task_type: str, payload: Dict[str, Any]) -> str:
    encoded = json.dumps({"task": task_type, "payload": payload}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class _CacheEntry:
    value: Dict[str, Any]
    expires_at: float


class AICache:
    """In-memory TTL cache for AI evaluations."""

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.expires_at < time.time():
                del self._store[key]
                return None
            return item.value

    async def set(self, key: str, value: Dict[str, Any]) -> None:
        async with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)


class AIEngine:
    """
    Async AI orchestration layer.
    - Supports timeout bounded calls.
    - Caches repeated evaluations.
    - Falls back safely on failures.
    """

    def __init__(self) -> None:
        self.enabled = settings.ai_enabled
        self.timeout_seconds = settings.ai_timeout_seconds
        self.cache = AICache(settings.ai_cache_ttl_seconds)
        self.cache_ttl_seconds = settings.ai_cache_ttl_seconds
        self.max_batch_size = settings.ai_max_batch_size

    async def evaluate(
        self,
        task_type: str,
        payload: Dict[str, Any],
        model_executor: Callable[[Dict[str, Any]], "asyncio.Future[Dict[str, Any]]"] | None = None,
        fallback: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if fallback is None:
            fallback = {
                "score": 5.0,
                "reasoning": "Default fallback advisory.",
                "tags": ["fallback"],
                "source": "fallback",
            }
        if not self.enabled:
            result = {**fallback, "ai_enabled": False, "explainability": "AI disabled by configuration"}
            self._log_decision(task_type, payload, result, latency_ms=0, impact="none")
            return result

        key = _stable_key(task_type, payload)
        cached = await self.cache.get(key)
        if cached:
            cached_result = {**cached, "cache_hit": True}
            self._log_decision(task_type, payload, cached_result, latency_ms=0, impact="cache")
            return cached_result

        started = time.time()
        if model_executor is None:
            async def default_executor(data: Dict[str, Any]) -> Dict[str, Any]:
                await asyncio.sleep(0.02)
                signal = float(data.get("signal_strength", 0.5))
                liquidity = float(data.get("liquidity", data.get("volume_24h", 0.0)))
                spread = float(data.get("spread_bps", 120.0))
                score = min(
                    10.0,
                    max(0.0, (signal * 10.0) + (1.2 if spread < 80 else 0.2) + (0.8 if liquidity > 50_000 else 0.0)),
                )
                confidence = max(0.1, min(0.95, 0.35 + (score / 15.0)))
                return {
                    "score": round(score, 2),
                    "reasoning": (
                        "High liquidity and tighter spread improve expected execution quality."
                        if score >= 6.5
                        else "Signal is weak or market microstructure is less attractive."
                    ),
                    "tags": ["advisory"],
                    "confidence": round(confidence, 3),
                    "source": "ai",
                }
            model_executor = default_executor

        try:
            model_output = await asyncio.wait_for(model_executor(payload), timeout=self.timeout_seconds)
            latency_ms = int((time.time() - started) * 1000)
            result = {**model_output, "cache_hit": False, "ai_enabled": True}
            await self.cache.set(key, result)
            self._log_decision(task_type, payload, result, latency_ms=latency_ms, impact="advisory")
            return result
        except Exception as exc:  # pylint: disable=broad-except
            latency_ms = int((time.time() - started) * 1000)
            logger.warning("AI evaluation failed task=%s error=%s", task_type, exc)
            result = {
                **fallback,
                "ai_enabled": True,
                "fallback_used": True,
                "explainability": f"AI fallback due to failure: {type(exc).__name__}",
            }
            self._log_decision(task_type, payload, result, latency_ms=latency_ms, impact="fallback")
            return result

    async def batch_evaluate(
        self,
        task_type: str,
        payloads: List[Dict[str, Any]],
        model_executor: Callable[[Dict[str, Any]], "asyncio.Future[Dict[str, Any]]"],
        fallback: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        limited = payloads[: self.max_batch_size]
        tasks = [self.evaluate(task_type, payload, model_executor, fallback) for payload in limited]
        return await asyncio.gather(*tasks)

    @staticmethod
    def _log_decision(
        task_type: str,
        model_input: Dict[str, Any],
        model_output: Dict[str, Any],
        latency_ms: int,
        impact: str,
    ) -> None:
        logger.info(
            "ai_decision task=%s latency_ms=%s impact=%s input=%s output=%s",
            task_type,
            latency_ms,
            impact,
            model_input,
            model_output,
        )
