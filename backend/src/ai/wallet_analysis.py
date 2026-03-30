"""
Wallet Behavior Analysis — AI classifies wallets for copy trading decisions.

This runs periodically (not on every trade) to build a profile of tracked wallets.
Results inform copy trading size multipliers and filtering.

Deterministic fallbacks:
- Win rate > 55% + 20+ trades → quality_score 6.0
- Win rate < 45% → quality_score 3.0
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import Cache
from .ai_engine import AIEngine, get_ai_engine

logger = get_logger(__name__)

_cache = Cache("ai:wallet", default_ttl=settings.ai_cache_ttl_seconds * 4)  # Longer TTL — data doesn't change fast

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "wallet_prompt.txt"


def _load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text()
    except FileNotFoundError:
        return "Analyze this wallet's trading behavior and return JSON classification."


def _deterministic_analysis(wallet_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback wallet scoring based on statistics alone."""
    win_rate = wallet_data.get("win_rate", 0.5)
    total_trades = wallet_data.get("total_trades", 0)
    avg_pnl_pct = wallet_data.get("avg_pnl_pct", 0)

    if total_trades < 10:
        quality_score = 4.0
        confidence = 0.2
        strategy_class = "unknown"
        copy_recommended = False
        caveat = "Insufficient trade history for reliable analysis."
    elif win_rate > 0.60 and avg_pnl_pct > 0.05:
        quality_score = 7.5
        confidence = 0.6
        strategy_class = "momentum"
        copy_recommended = True
        caveat = "Deterministic fallback score — AI analysis unavailable."
    elif win_rate < 0.45:
        quality_score = 3.0
        confidence = 0.7
        strategy_class = "noise_trader"
        copy_recommended = False
        caveat = "Low win rate suggests poor signal quality."
    else:
        quality_score = 5.5
        confidence = 0.4
        strategy_class = "unknown"
        copy_recommended = False
        caveat = "Average performance — monitor before enabling copy trade."

    return {
        "quality_score": quality_score,
        "strategy_class": strategy_class,
        "confidence": confidence,
        "summary": f"Wallet has {total_trades} trades with {win_rate:.1%} win rate.",
        "strengths": [],
        "weaknesses": [],
        "copy_trade_recommended": copy_recommended,
        "copy_trade_caveat": caveat,
        "_fallback": True,
    }


async def analyze_wallet(
    wallet_data: Dict[str, Any],
    trade_history: List[Dict[str, Any]],
    engine: Optional[AIEngine] = None,
    wallet_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a wallet's trading behavior.

    Args:
        wallet_data: Wallet stats (win_rate, total_trades, pnl, etc.)
        trade_history: Last N trades with market, side, price, size, outcome
        engine: AI engine (uses singleton if None)
        wallet_id: DB wallet ID for log linking

    Returns:
        Analysis dict with quality_score, strategy_class, confidence, etc.
    """
    if engine is None:
        engine = get_ai_engine()

    fallback = _deterministic_analysis(wallet_data)

    if not engine.is_available or len(trade_history) < 5:
        if len(trade_history) < 5:
            logger.info("wallet_analysis_skipped_insufficient_trades", wallet=wallet_data.get("address"))
        return fallback

    user_prompt = _build_wallet_prompt(wallet_data, trade_history)

    result, cache_hit = await engine.complete(
        system_prompt=_load_system_prompt(),
        user_prompt=user_prompt,
        component="wallet_analysis",
        context={"wallet": wallet_data, "trade_count": len(trade_history)},
        cache=_cache,
        parse_json=True,
        fallback=fallback,
        wallet_id=wallet_id,
    )

    return result or fallback


def _build_wallet_prompt(wallet_data: Dict[str, Any], trades: List[Dict[str, Any]]) -> str:
    recent = trades[-30:] if len(trades) > 30 else trades
    trade_lines = "\n".join(
        f"  - {t.get('timestamp', '?')} | {t.get('condition_id', '?')[:12]} | "
        f"{t.get('side', '?')} {t.get('outcome', '?')} @ {t.get('price', '?')} | "
        f"size={t.get('size', '?')}"
        for t in recent
    )

    return f"""WALLET ANALYSIS REQUEST:

Address: {wallet_data.get('address', 'N/A')}

AGGREGATE STATS:
- Total Trades: {wallet_data.get('total_trades', 0)}
- Win Rate: {wallet_data.get('win_rate', 0):.1%}
- Avg PnL per trade: {wallet_data.get('avg_pnl_pct', 0):.2%}
- Total Volume: ${wallet_data.get('total_volume_usdc', 0):,.0f}
- Active since: {wallet_data.get('first_seen_at', 'unknown')}

RECENT TRADE HISTORY (last {len(recent)} trades):
{trade_lines}

Analyze this wallet's behavior and return your JSON classification."""
