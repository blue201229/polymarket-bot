"""
AI-assisted anomaly and risk hints (Phase 4+).
Emits warnings only; risk engine may tighten limits or pause based on deterministic rules.
"""

from __future__ import annotations

from typing import Any

from ai.ai_engine import AIEngine, get_ai_engine


async def detect_anomalies(
    context: dict[str, Any],
    *,
    engine: AIEngine | None = None,
) -> dict[str, Any]:
    eng = engine or get_ai_engine()
    return await eng.run_scoring(
        market_summary={"feature": "anomaly", **context},
        kind="anomaly",
    )
