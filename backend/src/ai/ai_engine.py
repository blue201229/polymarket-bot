from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Optional

import orjson
from cachetools import TTLCache

from backend.src.config import settings
from backend.src.core.logging import get_logger

logger = get_logger("ai.engine")


class AIResponse:
    __slots__ = ("content", "model", "provider", "latency_ms", "tokens_used", "cached")

    def __init__(
        self,
        content: str,
        model: str = "",
        provider: str = "",
        latency_ms: int = 0,
        tokens_used: int = 0,
        cached: bool = False,
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.latency_ms = latency_ms
        self.tokens_used = tokens_used
        self.cached = cached

    def parse_json(self) -> dict[str, Any]:
        text = self.content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        return orjson.loads(text)


class AIEngine:
    """
    Unified AI engine abstracting provider-specific calls.

    Responsibilities:
    - Route to correct provider (Anthropic / OpenAI)
    - Enforce timeout (max ai_timeout_seconds)
    - Cache repeated evaluations (TTL-based)
    - Provide fallback on failure (returns None, never blocks pipeline)
    - Log every call: input, output, latency, success/failure
    """

    def __init__(self) -> None:
        self._cache: TTLCache = TTLCache(
            maxsize=1024, ttl=settings.ai_cache_ttl_seconds
        )
        self._anthropic_client: Any = None
        self._openai_client: Any = None

    def _get_anthropic(self) -> Any:
        if self._anthropic_client is None:
            try:
                import anthropic
                self._anthropic_client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
            except Exception as e:
                logger.error("Failed to init Anthropic client", error=str(e))
                raise
        return self._anthropic_client

    def _get_openai(self) -> Any:
        if self._openai_client is None:
            try:
                import openai
                self._openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            except Exception as e:
                logger.error("Failed to init OpenAI client", error=str(e))
                raise
        return self._openai_client

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        raw = f"{model}:{system}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def complete(
        self,
        prompt: str,
        system: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        use_cache: bool = True,
        timeout: Optional[float] = None,
    ) -> Optional[AIResponse]:
        if not settings.ai_enabled:
            logger.debug("AI disabled, skipping call")
            return None

        provider = provider or settings.ai_default_provider
        model = model or settings.ai_default_model
        timeout = timeout or settings.ai_timeout_seconds

        cache_key = self._cache_key(prompt, system, model)
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug("AI cache hit", model=model)
            return AIResponse(
                content=cached["content"],
                model=model,
                provider=provider,
                latency_ms=0,
                tokens_used=0,
                cached=True,
            )

        start = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._call_provider(
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=timeout,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            if use_cache:
                self._cache[cache_key] = {
                    "content": response.content,
                    "tokens": response.tokens_used,
                }

            response.latency_ms = latency_ms
            logger.info(
                "AI call completed",
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                tokens=response.tokens_used,
            )
            return response

        except asyncio.TimeoutError:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "AI call timed out",
                provider=provider,
                model=model,
                timeout=timeout,
                latency_ms=latency_ms,
            )
            return None
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "AI call failed",
                provider=provider,
                model=model,
                error=str(e),
                latency_ms=latency_ms,
            )
            return None

    async def _call_provider(
        self,
        provider: str,
        model: str,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> AIResponse:
        if provider == "anthropic":
            return await self._call_anthropic(model, prompt, system, temperature, max_tokens)
        elif provider == "openai":
            return await self._call_openai(model, prompt, system, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

    async def _call_anthropic(
        self, model: str, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> AIResponse:
        client = self._get_anthropic()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = await client.messages.create(**kwargs)
        content = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return AIResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=tokens,
        )

    async def _call_openai(
        self, model: str, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> AIResponse:
        client = self._get_openai()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return AIResponse(
            content=content,
            model=model,
            provider="openai",
            tokens_used=tokens,
        )

    async def batch_complete(
        self,
        requests: list[dict[str, Any]],
        max_concurrency: int = 5,
    ) -> list[Optional[AIResponse]]:
        """Run multiple AI calls concurrently with bounded parallelism."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_call(req: dict[str, Any]) -> Optional[AIResponse]:
            async with semaphore:
                return await self.complete(**req)

        return await asyncio.gather(*[_bounded_call(r) for r in requests])

    def clear_cache(self) -> None:
        self._cache.clear()


ai_engine = AIEngine()
