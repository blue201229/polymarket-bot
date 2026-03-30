"""
AI-assisted market scoring (assistant layer only).
Hard filters run before this; risk engine never reads this as authoritative.
"""

from __future__ import annotations

from typing import Any

from ai.ai_engine import AIEngine, get_ai_engine


async def score_market(
    market: dict[str, Any],
    *,
    engine: AIEngine | None = None,
) -> dict[str, Any]:
    """
    Produce score 0-10, reasoning, tags. When AI is off, returns explainable disabled state.
    """
    eng = engine or get_ai_engine()
    summary = {
        "feature": "market_scoring",
        "question": market.get("question"),
        "volume": market.get("volume"),
        "liquidity": market.get("liquidity"),
        "active": market.get("active"),
        "closed": market.get("closed"),
    }
    result = await eng.run_scoring(market_summary=summary, kind="market")
    # Normalize score to 0-10 when present
    score = result.get("score")
    if isinstance(score, (int, float)) and score is not None:
        result["score"] = max(0.0, min(10.0, float(score)))
    return result
