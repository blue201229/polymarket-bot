"""
AI Engine — abstracts model calls with caching, batching, timeout, and fallback.

Design decisions:
- All calls are async and have a hard timeout (AI_TIMEOUT_SECONDS).
- Results are cached by input hash to avoid redundant API calls.
- On any AI failure, the system falls back to deterministic defaults.
- Never blocks the execution pipeline.
"""
import asyncio
import hashlib
import json
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import anthropic
import openai

from src.core.config import settings
from src.core.logging import get_logger, ai_decision_logger
from src.core.redis_client import Cache
from src.core.exceptions import AIError, AITimeoutError

logger = get_logger(__name__)

# Shared caches per component
_market_cache = Cache("ai:market", default_ttl=settings.ai_cache_ttl_seconds)
_wallet_cache = Cache("ai:wallet", default_ttl=settings.ai_cache_ttl_seconds * 2)
_signal_cache = Cache("ai:signal", default_ttl=60)  # Short TTL — signals are time-sensitive


class AIEngine:
    """
    Central AI engine. All components use this to make model calls.
    Supports: Anthropic Claude (primary), OpenAI (fallback).
    """

    def __init__(self):
        self._anthropic: Optional[anthropic.AsyncAnthropic] = None
        self._openai: Optional[openai.AsyncOpenAI] = None

        if settings.anthropic_api_key:
            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        if settings.openai_api_key:
            self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)

        self._available = settings.ai_available
        logger.info(
            "ai_engine_initialized",
            anthropic=bool(self._anthropic),
            openai=bool(self._openai),
            enabled=self._available,
        )

    @property
    def is_available(self) -> bool:
        return self._available

    def _hash_input(self, prompt: str, context: Dict[str, Any]) -> str:
        payload = json.dumps({"prompt": prompt, "context": context}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        component: str,
        context: Dict[str, Any],
        cache: Optional[Cache] = None,
        parse_json: bool = True,
        fallback: Optional[Dict[str, Any]] = None,
        market_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        signal_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Execute an AI completion call.

        Returns:
            (result, cache_hit) — result is None if AI is unavailable or failed.
            Caller MUST handle None by using the fallback or skipping the AI layer.
        """
        if not self._available:
            return fallback, False

        input_hash = self._hash_input(user_prompt, context)

        # Check cache
        if cache:
            cached = await cache.get(input_hash)
            if cached is not None:
                ai_decision_logger.log(
                    component=component,
                    input_data=context,
                    output_data=cached,
                    latency_ms=0,
                    model="cached",
                    cache_hit=True,
                )
                return cached, True

        start = time.monotonic()
        try:
            raw_result = await asyncio.wait_for(
                self._call_model(system_prompt, user_prompt),
                timeout=settings.ai_timeout_seconds,
            )
            latency_ms = (time.monotonic() - start) * 1000

            if parse_json:
                result = self._parse_json_response(raw_result)
            else:
                result = {"text": raw_result}

            if result is None:
                result = fallback

            if cache and result:
                await cache.set(input_hash, result)

            ai_decision_logger.log(
                component=component,
                input_data=context,
                output_data=result or {},
                latency_ms=latency_ms,
                model=settings.anthropic_model,
                cache_hit=False,
            )

            await self._persist_log(
                component=component,
                model=settings.anthropic_model,
                input_hash=input_hash,
                prompt_summary=user_prompt[:500],
                output_raw=raw_result,
                output_parsed=result,
                latency_ms=latency_ms,
                cache_hit=False,
                success=True,
                market_id=market_id,
                trade_id=trade_id,
                wallet_id=wallet_id,
                signal_id=signal_id,
            )

            return result, False

        except asyncio.TimeoutError:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning("ai_timeout", component=component, latency_ms=latency_ms)
            await self._persist_log(
                component=component,
                model=settings.anthropic_model,
                input_hash=input_hash,
                latency_ms=latency_ms,
                success=False,
                error_message="timeout",
            )
            return fallback, False

        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("ai_error", component=component, error=str(exc))
            await self._persist_log(
                component=component,
                model=settings.anthropic_model,
                input_hash=input_hash,
                latency_ms=latency_ms,
                success=False,
                error_message=str(exc)[:512],
            )
            return fallback, False

    async def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        """Try Anthropic first, fall back to OpenAI."""
        if self._anthropic:
            response = await self._anthropic.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text

        if self._openai:
            response = await self._openai.chat.completions.create(
                model=settings.openai_model,
                max_tokens=settings.anthropic_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        raise AIError("No AI provider configured")

    def _parse_json_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from AI response, handling markdown code fences."""
        text = raw.strip()
        # Strip markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract the first JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning("ai_json_parse_failed", raw_preview=raw[:200])
            return None

    async def batch_complete(
        self,
        requests: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Optional[Dict[str, Any]]]:
        """Process multiple AI requests concurrently with a concurrency limit."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _single(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with semaphore:
                result, _ = await self.complete(**req)
                return result

        return await asyncio.gather(*[_single(r) for r in requests])

    async def _persist_log(self, **kwargs) -> None:
        """Persist AI decision log to database (best-effort, non-blocking)."""
        try:
            from src.core.database import db_session
            from src.models.ai_log import AILog

            async with db_session() as session:
                log = AILog(**{k: v for k, v in kwargs.items() if v is not None})
                session.add(log)
        except Exception as exc:
            logger.warning("ai_log_persist_failed", error=str(exc))


# Module-level singleton
_engine_instance: Optional[AIEngine] = None


def get_ai_engine() -> AIEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AIEngine()
    return _engine_instance
