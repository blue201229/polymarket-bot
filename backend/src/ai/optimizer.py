from __future__ import annotations

from ai.ai_engine import AIEngine
from app.domain.models import OptimizationSuggestion


class ParameterOptimizerService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine

    async def suggest(self, metrics: dict) -> list[OptimizationSuggestion]:
        pnl_trend = float(metrics.get("pnl_trend", 0.0))
        suggestion = OptimizationSuggestion(
            parameter="entry_threshold",
            current_value=str(metrics.get("entry_threshold", 0.62)),
            suggested_value=str(0.66 if pnl_trend < 0 else metrics.get("entry_threshold", 0.62)),
            rationale="Phase 1 scaffold. Keep human review in the loop for all parameter changes.",
        )
        return [suggestion]
