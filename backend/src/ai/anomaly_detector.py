from __future__ import annotations

import asyncio

from core.models import AIExplanation, AnomalyResponse

from .ai_engine import AIEngine


async def detect_anomaly(engine: AIEngine, req: AIExplanation) -> AnomalyResponse:
    async def _executor(payload: dict[str, float]) -> dict[str, object]:
        await asyncio.sleep(0.02)
        spread = float(payload.get("spread_bps", 0.0))
        liquidity = float(payload.get("liquidity", 0.0))
        wallet_risk = float(payload.get("wallet_risk_score", 0.0))
        severity = min(
            10.0,
            max(0.0, spread / 80.0 + wallet_risk + (0.5 if liquidity < 10_000 else 0.0)),
        )
        if severity >= 8.0:
            recommendation = "pause-suggested"
            warnings = ["critical anomaly", "consider temporary strategy pause"]
        elif severity >= 6.0:
            recommendation = "tighten-risk"
            warnings = ["elevated anomaly", "tighten spread/size limits"]
        else:
            recommendation = "continue"
            warnings = ["no major anomaly detected"]
        return {
            "severity": round(severity, 2),
            "warnings": warnings,
            "recommendation": recommendation,
            "reasoning": "Anomaly derived from spread, liquidity, and wallet-risk behavior.",
            "source": "ai",
        }

    metrics = req.metrics
    payload = {
        "spread_bps": float(metrics.get("spread_bps", 0.0)),
        "liquidity": float(metrics.get("liquidity", 0.0)),
        "wallet_risk_score": float(metrics.get("wallet_risk_score", 0.0)),
    }
    fallback = {
        "severity": 3.0,
        "warnings": ["fallback anomaly profile"],
        "recommendation": "continue",
        "reasoning": "Fallback anomaly profile (AI unavailable).",
        "source": "fallback",
    }
    result = await engine.evaluate(
        task_type="anomaly_detection",
        payload=payload,
        model_executor=_executor,
        fallback=fallback,
    )
    return AnomalyResponse(
        severity=float(result["severity"]),
        warnings=[str(v) for v in result["warnings"]],
        recommendation=str(result["recommendation"]),
        reasoning=f"{req.context}: {result['reasoning']}",
        source=str(result["source"]),
    )
