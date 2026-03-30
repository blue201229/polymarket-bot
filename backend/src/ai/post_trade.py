"""
Post-Trade Analysis — AI reviews completed trades to generate insights.

Runs asynchronously after trades close. Does not affect live trading.
Outputs are stored as insight logs and surfaced in the UI.
"""
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import Cache
from .ai_engine import AIEngine, get_ai_engine

logger = get_logger(__name__)

_cache = Cache("ai:post_trade", default_ttl=86400)  # 24h — historical analysis is stable

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "post_trade_prompt.txt"


def _load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text()
    except FileNotFoundError:
        return "Analyze this completed trade and return JSON insights."


async def analyze_trade(
    trade_data: Dict[str, Any],
    market_data: Dict[str, Any],
    engine: Optional[AIEngine] = None,
    trade_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a completed trade.

    Args:
        trade_data: Trade record with entry price, exit price, PnL, AI confidence at time
        market_data: Market state at entry and exit
        engine: AI engine (uses singleton if None)
        trade_id: DB trade ID

    Returns:
        Analysis dict with outcome explanation, execution quality, strategy feedback
    """
    if engine is None:
        engine = get_ai_engine()

    fallback = {
        "outcome": "win" if trade_data.get("pnl_usdc", 0) > 0 else "loss",
        "result_explanation": "AI post-trade analysis unavailable.",
        "execution_quality": "unknown",
        "signal_was_correct": None,
        "missed_opportunity": None,
        "strategy_feedback": "AI unavailable — review manually.",
        "pattern_tag": "unknown",
        "_fallback": True,
    }

    if not engine.is_available:
        return fallback

    user_prompt = _build_post_trade_prompt(trade_data, market_data)

    result, _ = await engine.complete(
        system_prompt=_load_system_prompt(),
        user_prompt=user_prompt,
        component="post_trade_analysis",
        context={"trade_id": trade_id, "pnl": trade_data.get("pnl_usdc")},
        cache=_cache,
        parse_json=True,
        fallback=fallback,
        trade_id=trade_id,
    )

    return result or fallback


def _build_post_trade_prompt(trade_data: Dict[str, Any], market_data: Dict[str, Any]) -> str:
    return f"""POST-TRADE ANALYSIS:

TRADE RECORD:
- Strategy: {trade_data.get('source', 'N/A')}
- Side: {trade_data.get('side', 'N/A')} {trade_data.get('outcome', 'N/A')}
- Entry Price: {trade_data.get('target_price', 'N/A')}
- Executed Price: {trade_data.get('executed_price', 'N/A')}
- Slippage: {trade_data.get('slippage_pct', 'N/A')}
- Size: ${trade_data.get('size_usdc', 0):.2f} USDC
- PnL: ${trade_data.get('pnl_usdc', 0):.2f} ({trade_data.get('pnl_pct', 0):.2%})

AI SIGNAL AT TIME OF TRADE:
- AI Confidence: {trade_data.get('ai_confidence', 'N/A')}
- AI Decision: {trade_data.get('ai_decision', 'N/A')}
- AI Reasoning: {trade_data.get('ai_reasoning', 'N/A')}

MARKET CONTEXT:
- Market: {market_data.get('question', 'N/A')[:100]}
- Price at entry: {market_data.get('price_at_entry', 'N/A')}
- Price at exit: {market_data.get('price_at_exit', 'N/A')}
- Spread at entry: {market_data.get('spread_at_entry', 'N/A')}

Analyze this trade and return your JSON insights."""
