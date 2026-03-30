"""
Trade Signal Filtering — AI evaluates trade signals before risk engine review.

Critical design:
- AI filter runs BEFORE risk engine, as an advisory gate.
- If AI says 'skip': we log the skip but the trade may still execute if operator overrides.
- If AI says 'execute': trade STILL passes through the risk engine.
- AI can never force a trade or bypass risk rules.

Execution pipeline:
  Strategy signal → AI filter (advisory) → Risk engine (hard rules) → Execution
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import Cache
from .ai_engine import AIEngine, get_ai_engine

logger = get_logger(__name__)

_cache = Cache("ai:signal", default_ttl=60)  # Very short TTL — market conditions change fast

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "trade_prompt.txt"


def _load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text()
    except FileNotFoundError:
        return "Evaluate this trade signal and return JSON with confidence and decision."


def _deterministic_filter(signal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback when AI is unavailable.
    Uses spread, liquidity, and historical base rates.
    """
    spread_pct = signal_data.get("spread_pct", 0.05)
    liquidity = signal_data.get("liquidity", 0)
    historical_win_rate = signal_data.get("strategy_win_rate", 0.5)

    confidence = historical_win_rate

    if spread_pct > 0.08:
        confidence -= 0.15
    if liquidity < 5_000:
        confidence -= 0.20
    if spread_pct < 0.02:
        confidence += 0.05

    confidence = max(0.0, min(1.0, confidence))

    if confidence < 0.45:
        decision = "skip"
    elif confidence < 0.55:
        decision = "wait"
    else:
        decision = "execute"

    size_modifier = min(1.5, max(0.5, confidence / 0.6))

    return {
        "confidence": round(confidence, 3),
        "decision": decision,
        "size_modifier": round(size_modifier, 2),
        "reasoning": "Deterministic fallback filter based on spread and historical win rate (AI unavailable).",
        "key_concern": "AI filter unavailable — using statistical fallback.",
        "urgency": "medium",
        "_fallback": True,
    }


async def filter_signal(
    signal_data: Dict[str, Any],
    market_context: Dict[str, Any],
    engine: Optional[AIEngine] = None,
    signal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate a trade signal with AI.

    Args:
        signal_data: Dict with strategy, side, outcome, target_price,
                     suggested_size_usdc, strategy_win_rate, strategy_trade_count
        market_context: Dict with spread_pct, liquidity, volume_24h,
                        best_bid, best_ask, question
        engine: AI engine (uses singleton if None)
        signal_id: DB signal ID for log linking

    Returns:
        Filter result with confidence, decision, size_modifier, reasoning
    """
    if engine is None:
        engine = get_ai_engine()

    combined = {**signal_data, **market_context}
    fallback = _deterministic_filter(combined)

    if not engine.is_available:
        return fallback

    user_prompt = _build_trade_prompt(signal_data, market_context)

    result, _ = await engine.complete(
        system_prompt=_load_system_prompt(),
        user_prompt=user_prompt,
        component="trade_filter",
        context=combined,
        cache=_cache,
        parse_json=True,
        fallback=fallback,
        signal_id=signal_id,
    )

    if result is None:
        return fallback

    result["_fallback"] = result.get("_fallback", False)
    return result


def _build_trade_prompt(signal_data: Dict[str, Any], market_context: Dict[str, Any]) -> str:
    return f"""TRADE SIGNAL EVALUATION:

SIGNAL:
- Strategy: {signal_data.get('strategy', 'N/A')}
- Side: {signal_data.get('side', 'N/A')} {signal_data.get('outcome', 'N/A')}
- Target Price: {signal_data.get('target_price', 'N/A')}
- Suggested Size: ${signal_data.get('suggested_size_usdc', 0):.2f} USDC
- Strategy Historical Win Rate: {signal_data.get('strategy_win_rate', 0):.1%} ({signal_data.get('strategy_trade_count', 0)} trades)

MARKET CONTEXT:
- Market: {market_context.get('question', 'N/A')[:100]}
- Best Bid: {market_context.get('best_bid', 'N/A')}
- Best Ask: {market_context.get('best_ask', 'N/A')}
- Spread %: {market_context.get('spread_pct', 'N/A')}
- 24h Volume: ${market_context.get('volume_24h', 0):,.0f}
- Liquidity: ${market_context.get('liquidity', 0):,.0f}
- AI Market Score: {market_context.get('ai_score', 'N/A')}

Evaluate this trade signal and return your JSON assessment."""
