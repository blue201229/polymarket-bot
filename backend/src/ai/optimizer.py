"""
Parameter optimization suggestions (Phase 5+).
Suggestions are never auto-applied; validated by operators / deterministic rules.
"""

from __future__ import annotations

from typing import Any

from ai.ai_engine import AIEngine, get_ai_engine


async def suggest_parameters(
    performance_context: dict[str, Any],
    *,
    engine: AIEngine | None = None,
) -> dict[str, Any]:
    eng = engine or get_ai_engine()
    return await eng.run_scoring(
        market_summary={"feature": "optimizer", **performance_context},
        kind="optimizer",
    )
