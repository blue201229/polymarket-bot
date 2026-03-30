from __future__ import annotations

import asyncio
from typing import Any

from core.models import AiScore, Market, MarketScoreResult

from .ai_engine import AIEngine


async def score_market(engine: AIEngine, market: Market) -> MarketScoreResult:
    payload = {
        "market_id": market.market_id,
        "question": market.question,
        "category": market.category,
        "volume_24h": market.volume_24h,
        "spread_bps": market.spread_bps,
    }
    fallback = {
        "score": 5.0,
        "reasoning": "Fallback score used because AI unavailable.",
        "tags": ["fallback"],
        "source": "fallback",
    }

    async def _executor(data: dict[str, Any]) -> dict[str, Any]:
        # Phase 1 mock heuristic model (replace with provider adapters in Phase 2).
        await asyncio.sleep(0.03)
        score = 5.0
        tags: list[str] = []
        if float(data["volume_24h"]) > 500_000:
            score += 2.0
            tags.append("high-volume")
        if float(data["spread_bps"]) < 80:
            score += 1.5
            tags.append("tight-spread")
        if str(data["category"]) == "crypto":
            score += 0.5
            tags.append("high-volatility")
        score = max(0.0, min(10.0, score))
        return {
            "score": score,
            "reasoning": "Scored using liquidity/spread/category quality factors.",
            "tags": tags,
            "source": "ai",
        }

    result = await engine.evaluate(
        task_type="market_scoring",
        payload=payload,
        model_executor=_executor,
        fallback=fallback,
    )

    return MarketScoreResult(
        market_id=market.market_id,
        ai_enabled=bool(result.get("ai_enabled", False)),
        score=AiScore(
            score=float(result.get("score", 5.0)),
            reasoning=str(result.get("reasoning", "")),
            tags=[str(x) for x in result.get("tags", [])],
            source=str(result.get("source", "fallback")),  # type: ignore[arg-type]
        ),
    )
