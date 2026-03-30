from __future__ import annotations

from core.models import AITradeFilterRequest, AITradeFilterResponse

from .ai_engine import AIEngine

async def filter_trade_signal(engine: AIEngine, req: AITradeFilterRequest) -> AITradeFilterResponse:
    payload = req.model_dump()
    payload["signal_strength"] = max(
        0.0,
        min(
            1.0,
            (req.historical_win_rate * 0.65)
            + (0.35 * max(0.0, 1.0 - (req.spread_bps / 250.0))),
        ),
    )
    result = await engine.evaluate(
        task_type="trade_signal_filter",
        payload=payload,
    )

    if req.spread_bps > 180:
        action = "skip"
        size_modifier = 0.50
        explanation = "Skipped: low liquidity + wide spread."
    elif req.recent_volatility > 0.3:
        action = "review"
        size_modifier = 0.75
        explanation = "High volatility: reduce size and review."
    else:
        action = "execute" if float(result.get("confidence", 0.5)) >= 0.60 else "review"
        size_modifier = 1.00 if action == "execute" else 0.90
        explanation = "Microstructure acceptable; pass through deterministic risk checks."

    return AITradeFilterResponse(
        signal_id=req.signal_id,
        confidence_score=float(result.get("confidence", 0.5)),
        suggested_size_modifier=size_modifier,
        suggested_action=action,
        explanation=f"{explanation} {str(result.get('reasoning', 'AI advisory unavailable.'))}",
        source=str(result.get("source", "fallback")),
    )
