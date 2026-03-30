from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Protocol

from app.core.config import Settings
from app.domain.models import AIScore

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent / "prompts"


class AIProvider(Protocol):
    async def generate(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    async def generate_batch(self, prompt_name: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


@dataclass
class CacheEntry:
    expires_at: float
    value: dict[str, Any]


class MockAIProvider:
    async def generate(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.02)
        return self._heuristic_response(prompt_name, payload)

    async def generate_batch(self, prompt_name: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        await asyncio.sleep(0.05)
        return [self._heuristic_response(prompt_name, payload) for payload in payloads]

    def _heuristic_response(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if prompt_name == "market_prompt.txt":
            clarity = payload.get("resolution_clarity", 0.0)
            volatility = min(payload.get("volume_24h", 0.0) / 80_000, 1.0)
            inefficiency = abs(payload.get("hype_score", 0.5) - payload.get("news_density", 0.5))
            score = round(min(10.0, 4.0 * clarity + 3.0 * volatility + 3.0 * inefficiency), 2)
            tags = []
            if volatility > 0.7:
                tags.append("high volatility")
            if clarity < 0.7:
                tags.append("uncertain resolution")
            if inefficiency > 0.2:
                tags.append("inefficiency")
            reasoning = (
                "Strong narrative/flow" if score >= 7 else "Mixed narrative quality"
            ) + f" | clarity={clarity:.2f}, vol={volatility:.2f}, ineff={inefficiency:.2f}"
            return {"score": score, "reasoning": reasoning, "tags": tags}

        return {"score": 5.0, "reasoning": "Neutral advisory result", "tags": ["neutral"]}


class AIEngine:
    def __init__(self, provider: AIProvider, *, enabled: bool, timeout_seconds: float, cache_ttl_seconds: int) -> None:
        self.provider = provider
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, CacheEntry] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIEngine":
        provider: AIProvider = MockAIProvider()
        return cls(
            provider,
            enabled=settings.ai_enabled,
            timeout_seconds=settings.ai_timeout_seconds,
            cache_ttl_seconds=settings.ai_cache_ttl_seconds,
        )

    async def evaluate(
        self,
        prompt_name: str,
        payload: dict[str, Any],
        fallback_factory: Callable[[str], AIScore],
        *,
        decision_impact: str,
    ) -> AIScore:
        if not self.enabled:
            return fallback_factory("disabled")

        cache_key = self._cache_key(prompt_name, payload)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return AIScore(**cached, latency_ms=0, decision_impact=decision_impact)

        started = time.perf_counter()
        try:
            raw = await asyncio.wait_for(self.provider.generate(prompt_name, payload), timeout=self.timeout_seconds)
            latency_ms = int((time.perf_counter() - started) * 1000)
            result = AIScore(
                source="ai",
                score=float(raw["score"]),
                reasoning=str(raw["reasoning"]),
                tags=list(raw.get("tags", [])),
                latency_ms=latency_ms,
                decision_impact=decision_impact,
            )
            self._set_cache(cache_key, result.model_dump(exclude={"latency_ms"}))
            self._log_event(prompt_name, payload, result)
            return result
        except Exception as exc:  # noqa: BLE001
            fallback = fallback_factory("fallback")
            logger.warning("ai_evaluation_failed prompt=%s error=%s", prompt_name, exc)
            self._log_event(prompt_name, payload, fallback)
            return fallback

    async def evaluate_batch(
        self,
        prompt_name: str,
        payloads: list[dict[str, Any]],
        fallback_factory: Callable[[dict[str, Any], str], AIScore],
        *,
        decision_impact: str,
    ) -> list[AIScore]:
        if not self.enabled:
            return [fallback_factory(payload, "disabled") for payload in payloads]

        uncached_indices: list[int] = []
        uncached_payloads: list[dict[str, Any]] = []
        results: list[AIScore | None] = [None] * len(payloads)

        for index, payload in enumerate(payloads):
            cached = self._get_cached(self._cache_key(prompt_name, payload))
            if cached is None:
                uncached_indices.append(index)
                uncached_payloads.append(payload)
            else:
                results[index] = AIScore(**cached, latency_ms=0, decision_impact=decision_impact)

        if uncached_payloads:
            started = time.perf_counter()
            try:
                raw_results = await asyncio.wait_for(
                    self.provider.generate_batch(prompt_name, uncached_payloads),
                    timeout=self.timeout_seconds,
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                for index, payload, raw in zip(uncached_indices, uncached_payloads, raw_results, strict=True):
                    result = AIScore(
                        source="ai",
                        score=float(raw["score"]),
                        reasoning=str(raw["reasoning"]),
                        tags=list(raw.get("tags", [])),
                        latency_ms=latency_ms,
                        decision_impact=decision_impact,
                    )
                    results[index] = result
                    self._set_cache(
                        self._cache_key(prompt_name, payload),
                        result.model_dump(exclude={"latency_ms"}),
                    )
                    self._log_event(prompt_name, payload, result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ai_batch_evaluation_failed prompt=%s error=%s", prompt_name, exc)
                for index, payload in zip(uncached_indices, uncached_payloads, strict=True):
                    fallback = fallback_factory(payload, "fallback")
                    results[index] = fallback
                    self._log_event(prompt_name, payload, fallback)

        return [result for result in results if result is not None]

    def load_prompt(self, prompt_name: str) -> str:
        return (PROMPTS_DIR / prompt_name).read_text(encoding="utf-8")

    def _cache_key(self, prompt_name: str, payload: dict[str, Any]) -> str:
        body = json.dumps({"prompt": prompt_name, "payload": payload}, sort_keys=True, default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _get_cached(self, cache_key: str) -> dict[str, Any] | None:
        entry = self._cache.get(cache_key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._cache.pop(cache_key, None)
            return None
        return entry.value

    def _set_cache(self, cache_key: str, value: dict[str, Any]) -> None:
        self._cache[cache_key] = CacheEntry(
            expires_at=time.time() + self.cache_ttl_seconds,
            value=value,
        )

    def _log_event(self, prompt_name: str, payload: dict[str, Any], result: AIScore) -> None:
        logger.info(
            "ai_decision prompt=%s input=%s output=%s latency_ms=%s decision_impact=%s",
            prompt_name,
            json.dumps(payload, default=str),
            result.model_dump_json(),
            result.latency_ms,
            result.decision_impact,
        )
