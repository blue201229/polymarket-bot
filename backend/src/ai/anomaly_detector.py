from __future__ import annotations

from ai.ai_engine import AIEngine
from app.domain.models import AnomalySignal


class AnomalyDetectionService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine

    async def scan(self, snapshot: dict) -> list[AnomalySignal]:
        spread = int(snapshot.get("spread_bps", 0))
        if spread > 250:
            return [
                AnomalySignal(
                    signal_type="spread_widening",
                    severity="medium",
                    message="Spread exceeds baseline threshold.",
                    suggested_action="tighten risk limits and monitor liquidity",
                )
            ]
        return []
