"""
Market Scoring — AI-assisted quality evaluation for Polymarket markets.

Flow:
1. Hard filters (deterministic) eliminate clearly bad markets
2. AI scores remaining markets on opportunity quality
3. Score is stored and surfaced in all frontends
4. Score is ADVISORY — low score doesn't block trading if other logic approves

Fallback: If AI unavailable, returns a deterministic score based on liquidity/spread.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import Cache
from .ai_engine import AIEngine, get_ai_engine

logger = get_logger(__name__)

_cache = Cache("ai:market_score", default_ttl=settings.ai_cache_ttl_seconds)

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "market_prompt.txt"


def _load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT.read_text()
    except FileNotFoundError:
        return "Score this Polymarket market from 0-10 and return JSON with score and reasoning."


def _deterministic_score(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback scoring when AI is unavailable.
    Uses liquidity, spread, and volume — fully deterministic and auditable.
    """
    liquidity = market_data.get("liquidity", 0)
    spread = market_data.get("spread_pct", 1.0)
    volume_24h = market_data.get("volume_24h", 0)

    score = 5.0  # neutral baseline
    tags = []

    if liquidity > 100_000:
        score += 1.5
        tags.append("high_liquidity")
    elif liquidity < 5_000:
        score -= 2.0
        tags.append("low_liquidity")

    if spread < 0.03:
        score += 1.0
    elif spread > 0.10:
        score -= 2.0
        tags.append("high_spread")

    if volume_24h > 50_000:
        score += 1.0
        tags.append("high_volume")
    elif volume_24h < 1_000:
        score -= 1.0

    score = max(0.0, min(10.0, score))

    return {
        "score": round(score, 2),
        "reasoning": "Deterministic fallback score based on liquidity, spread, and volume (AI unavailable).",
        "tags": tags,
        "volatility_potential": "medium",
        "resolution_clarity": "unknown",
        "recommended_action": "monitor" if score >= 5 else "avoid",
        "key_risk": "AI scoring unavailable — manual review recommended.",
        "_fallback": True,
    }


async def score_market(
    market_data: Dict[str, Any],
    engine: Optional[AIEngine] = None,
    market_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Score a single market.

    Args:
        market_data: Dict with keys: question, description, category, liquidity,
                     spread_pct, volume_24h, best_bid, best_ask, end_date
        engine: AI engine instance (uses singleton if None)
        market_id: DB market ID for log linking

    Returns:
        Dict with: score, reasoning, tags, volatility_potential,
                   resolution_clarity, recommended_action, key_risk, _fallback
    """
    if engine is None:
        engine = get_ai_engine()

    fallback = _deterministic_score(market_data)

    if not engine.is_available:
        return fallback

    user_prompt = _build_market_prompt(market_data)

    result, cache_hit = await engine.complete(
        system_prompt=_load_system_prompt(),
        user_prompt=user_prompt,
        component="market_scoring",
        context=market_data,
        cache=_cache,
        parse_json=True,
        fallback=fallback,
        market_id=market_id,
    )

    if result is None:
        return fallback

    result["_fallback"] = result.get("_fallback", False)
    result["_cache_hit"] = cache_hit
    return result


async def score_markets_batch(
    markets: List[Dict[str, Any]],
    engine: Optional[AIEngine] = None,
) -> List[Dict[str, Any]]:
    """Score multiple markets concurrently."""
    if engine is None:
        engine = get_ai_engine()

    if not engine.is_available:
        return [_deterministic_score(m) for m in markets]

    requests = [
        {
            "system_prompt": _load_system_prompt(),
            "user_prompt": _build_market_prompt(m),
            "component": "market_scoring_batch",
            "context": m,
            "cache": _cache,
            "parse_json": True,
            "fallback": _deterministic_score(m),
            "market_id": m.get("id"),
        }
        for m in markets
    ]

    results = await engine.batch_complete(requests, concurrency=5)
    return [r or _deterministic_score(markets[i]) for i, r in enumerate(results)]


def _build_market_prompt(market_data: Dict[str, Any]) -> str:
    return f"""MARKET TO EVALUATE:

Question: {market_data.get('question', 'N/A')}
Description: {market_data.get('description', 'N/A')[:500]}
Category: {market_data.get('category', 'N/A')}
End Date: {market_data.get('end_date', 'N/A')}

MARKET DATA:
- Best Bid: {market_data.get('best_bid', 'N/A')}
- Best Ask: {market_data.get('best_ask', 'N/A')}
- Spread %: {market_data.get('spread_pct', 'N/A')}
- 24h Volume: ${market_data.get('volume_24h', 0):,.0f}
- Total Liquidity: ${market_data.get('liquidity', 0):,.0f}
- Open Interest: ${market_data.get('open_interest', 0):,.0f}

Evaluate this market and return your JSON assessment."""


def passes_hard_filter(market_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Deterministic pre-filter before AI scoring.
    Markets failing this are never scored or traded.

    Returns: (passes, reason_if_rejected)
    """
    liquidity = market_data.get("liquidity", 0)
    spread_pct = market_data.get("spread_pct", 1.0)
    volume_24h = market_data.get("volume_24h", 0)

    if liquidity < 1_000:
        return False, "insufficient_liquidity"
    if spread_pct > 0.20:
        return False, "spread_too_wide"
    if volume_24h < 100:
        return False, "insufficient_volume"

    return True, ""
