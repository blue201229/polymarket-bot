"""
AI-assisted trade signal filtering (Phase 4+).
Suggests skip/execute and size modifiers; execution engine applies hard caps regardless.
"""

from __future__ import annotations

from typing import Any

from ai.ai_engine import AIEngine, get_ai_engine


async def filter_signal(
    signal_context: dict[str, Any],
    *,
    engine: AIEngine | None = None,
) -> dict[str, Any]:
    eng = engine or get_ai_engine()
    return await eng.run_scoring(
        market_summary={"feature": "trade_filter", **signal_context},
        kind="trade_filter",
    )
