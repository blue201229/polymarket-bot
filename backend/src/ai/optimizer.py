from __future__ import annotations

import asyncio
from typing import Any

from ai.ai_engine import AIEngine
from core.models import ParameterSuggestion, ParameterSuggestionRequest, ParameterSuggestionResponse


async def suggest_parameter_tuning(
    engine: AIEngine,
    req: ParameterSuggestionRequest,
) -> ParameterSuggestionResponse:
    recent_pnl = sum(req.recent_pnl) if req.recent_pnl else 0.0

    async def _mock_executor(payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.02)
        pnl = float(payload["recent_pnl_sum"])
        trend = str(payload["market_condition"])
        slippage_bps = 80.0 if pnl < 0 else 110.0
        if trend == "volatile":
            slippage_bps = max(60.0, slippage_bps - 20.0)
        cooldown = 90.0 if trend == "volatile" else 60.0
        size_modifier = 0.8 if pnl < 0 else 1.0
        entry_threshold = 0.64 if pnl < 0 else 0.60
        return {
            "slippage_limit_bps": slippage_bps,
            "entry_threshold": entry_threshold,
            "trade_size_modifier": size_modifier,
            "cooldown_seconds": cooldown,
            "reasoning": "Suggested from recent pnl trend and market condition; manual approval required.",
            "source": "ai",
            "confidence_score": 0.72 if pnl < 0 else 0.66,
        }

    fallback = {
        "slippage_limit_bps": 100.0,
        "entry_threshold": 0.60,
        "trade_size_modifier": 1.0,
        "cooldown_seconds": 60.0,
        "reasoning": "Fallback suggestion profile. Manual validation required.",
        "source": "fallback",
        "confidence_score": 0.35,
    }

    payload = {"recent_pnl_sum": recent_pnl, "market_condition": req.market_condition}
    result = await engine.evaluate(
        task_type="parameter_optimization",
        payload=payload,
        model_executor=_mock_executor,
        fallback=fallback,
    )

    suggestions = [
        ParameterSuggestion(
            parameter="slippage_limit_bps",
            current_value=100.0,
            suggested_value=float(result["slippage_limit_bps"]),
            rationale="Tighten slippage when pnl deteriorates or volatility rises.",
        ),
        ParameterSuggestion(
            parameter="entry_threshold",
            current_value=0.60,
            suggested_value=float(result["entry_threshold"]),
            rationale="Raise threshold during weak performance to improve selectivity.",
        ),
        ParameterSuggestion(
            parameter="trade_size_modifier",
            current_value=1.0,
            suggested_value=float(result["trade_size_modifier"]),
            rationale="Reduce size after drawdown; never auto-applied.",
        ),
        ParameterSuggestion(
            parameter="cooldown_seconds",
            current_value=60.0,
            suggested_value=float(result["cooldown_seconds"]),
            rationale="Increase cooldown in volatile conditions to reduce churn.",
        ),
    ]

    note = (
        f"AI advisory confidence={float(result.get('confidence_score', 0.5)):.2f}. "
        "Suggestions require manual validation before activation."
    )
    return ParameterSuggestionResponse(
        requires_validation=True,
        suggestions=suggestions,
        note=note,
    )
