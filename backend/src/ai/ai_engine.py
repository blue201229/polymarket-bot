"""
Central AI engine: async calls, timeouts, caching, logging, safe fallbacks.
Does not execute trades or override risk rules.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from polymarket_platform.config import Settings, get_settings

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class AICallLog:
    """Structured log line for every AI invocation (explainability)."""

    kind: str
    input_hash: str
    input_preview: str
    output_preview: str
    latency_ms: float
    cache_hit: bool
    error: str | None = None


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class AIEngine:
    """
    Abstracts model providers. Phase 1: no live API calls unless keys are set;
    returns conservative fallbacks with logged reasoning stubs.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._cache: dict[str, _CacheEntry] = {}
        self._call_logs: list[AICallLog] = []

    def _cache_key(self, kind: str, payload: dict[str, Any]) -> str:
        raw = json.dumps({"kind": kind, "p": payload}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.value

    def _set_cached(self, key: str, value: Any) -> None:
        ttl = max(0, self._settings.ai_cache_ttl_seconds)
        if ttl == 0:
            return
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    def load_prompt(self, name: str) -> str:
        path = _PROMPTS_DIR / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""

    async def run_scoring(
        self,
        *,
        market_summary: dict[str, Any],
        kind: str = "market",
    ) -> dict[str, Any]:
        """Generic scored response; real model wiring comes in later phases."""
        if not self._settings.ai_enabled:
            return self._disabled_fallback("market_scoring")

        key = self._cache_key(kind, market_summary)
        cached = self._get_cached(key)
        if cached is not None:
            self._log_call(
                kind,
                market_summary,
                cached,
                latency_ms=0.0,
                cache_hit=True,
                error=None,
            )
            return cached

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._invoke_model(kind, market_summary),
                timeout=self._settings.ai_request_timeout_seconds,
            )
        except TimeoutError:
            result = self._timeout_fallback("market_scoring")
            self._log_call(
                kind,
                market_summary,
                result,
                latency_ms=(time.perf_counter() - start) * 1000,
                cache_hit=False,
                error="timeout",
            )
            return result
        except Exception as e:  # noqa: BLE001 — assistant layer must not break callers
            logger.exception("AI invoke failed: %s", e)
            result = self._error_fallback(str(e))
            self._log_call(
                kind,
                market_summary,
                result,
                latency_ms=(time.perf_counter() - start) * 1000,
                cache_hit=False,
                error=repr(e),
            )
            return result

        self._set_cached(key, result)
        self._log_call(
            kind,
            market_summary,
            result,
            latency_ms=(time.perf_counter() - start) * 1000,
            cache_hit=False,
            error=None,
        )
        return result

    async def batch_run(
        self,
        items: list[dict[str, Any]],
        *,
        kind: str = "market",
    ) -> list[dict[str, Any]]:
        """Parallel async evaluation; does not block the event loop."""
        tasks = [self.run_scoring(market_summary=item, kind=kind) for item in items]
        return await asyncio.gather(*tasks)

    async def _invoke_model(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Phase 1: placeholder — wire Anthropic/OpenAI in Phase 2+.
        When no API keys are configured, return a neutral scored stub (not random profit claims).
        """
        has_anthropic = bool(self._settings.anthropic_api_key)
        has_openai = bool(self._settings.openai_api_key)
        if not has_anthropic and not has_openai:
            return {
                "score": 5.0,
                "reasoning": "AI assistant not configured: neutral placeholder score.",
                "tags": ["no_model_configured"],
                "assistant_only": True,
            }
        # Keys present but no HTTP client yet — same neutral stub until Phase 2 wiring.
        return {
            "score": 5.0,
            "reasoning": "Model client not yet implemented (Phase 2); neutral placeholder.",
            "tags": ["pending_implementation"],
            "assistant_only": True,
        }

    def _disabled_fallback(self, feature: str) -> dict[str, Any]:
        return {
            "score": None,
            "reasoning": f"AI assistant disabled ({feature}).",
            "tags": ["ai_disabled"],
            "assistant_only": True,
        }

    def _timeout_fallback(self, feature: str) -> dict[str, Any]:
        return {
            "score": None,
            "reasoning": f"AI assistant timed out ({feature}); no automated action taken.",
            "tags": ["ai_timeout"],
            "assistant_only": True,
        }

    def _error_fallback(self, err: str) -> dict[str, Any]:
        return {
            "score": None,
            "reasoning": f"AI assistant error; fallback applied: {err[:200]}",
            "tags": ["ai_error"],
            "assistant_only": True,
        }

    def _log_call(
        self,
        kind: str,
        input_payload: dict[str, Any],
        output: Any,
        *,
        latency_ms: float,
        cache_hit: bool,
        error: str | None,
    ) -> None:
        preview_in = json.dumps(input_payload, default=str)[:500]
        preview_out = json.dumps(output, default=str)[:500]
        ih = hashlib.sha256(preview_in.encode()).hexdigest()[:16]
        log = AICallLog(
            kind=kind,
            input_hash=ih,
            input_preview=preview_in,
            output_preview=preview_out,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            error=error,
        )
        self._call_logs.append(log)
        logger.info(
            "ai_call kind=%s latency_ms=%.2f cache=%s error=%s",
            kind,
            latency_ms,
            cache_hit,
            error,
        )


_engine: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine
