from __future__ import annotations

import asyncio
from typing import Any

from core.models import AIWalletRequest, AIWalletResponse

from .ai_engine import AIEngine


async def analyze_wallet(engine: AIEngine, req: AIWalletRequest) -> AIWalletResponse:
    async def mock_model(payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.01)
        consistency = float(payload.get("consistency_score", 5.0))
        risk = float(payload.get("risk_taking_score", 5.0))
        avg_size = float(payload.get("avg_position_size", 0.0))
        categories = payload.get("preferred_categories", [])
        categories = categories if isinstance(categories, list) else []
        normalized_consistency = consistency / 10.0
        normalized_risk = 1 - abs(risk - 6.0) / 10.0
        normalized_size = 0.7 if avg_size >= 300 else 0.4
        score = max(
            0.0,
            min(10.0, (normalized_consistency * 5.5) + (normalized_risk * 3.0) + (normalized_size * 1.5)),
        )
        style = "momentum"
        if avg_size < 150:
            style = "scalper"
        elif any(str(c).lower() == "crypto" for c in categories):
            style = "trend-follower"
        confidence = max(0.25, min(0.95, 0.35 + normalized_consistency * 0.5))
        return {
            "wallet_quality_score": round(score, 2),
            "strategy_classification": style,
            "confidence": round(confidence, 3),
            "reasoning": f"Classification={style}; consistency={consistency:.1f}, risk={risk:.1f}.",
            "source": "ai",
        }

    fallback = {
        "wallet_quality_score": 5.0,
        "strategy_classification": "unknown",
        "confidence": 0.4,
        "reasoning": "Fallback wallet profile: AI unavailable.",
        "source": "fallback",
    }
    out = await engine.evaluate(
        task_type="wallet_analysis",
        payload=req.model_dump(),
        model_executor=mock_model,
        fallback=fallback,
    )
    return AIWalletResponse(
        wallet=req.wallet,
        wallet_quality_score=float(out["wallet_quality_score"]),
        strategy_classification=str(out["strategy_classification"]),
        confidence=float(out["confidence"]),
        reasoning=str(out["reasoning"]),
        source=str(out["source"]),
    )
