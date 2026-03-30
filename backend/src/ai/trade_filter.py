from __future__ import annotations

from ai.ai_engine import AIEngine
from app.domain.models import TradeFilterDecision


class TradeFilterService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine

    async def evaluate_trade(self, signal: dict) -> TradeFilterDecision:
        liquidity_ok = float(signal.get("liquidity", 0)) >= 20_000
        spread_ok = int(signal.get("spread_bps", 999)) <= 150
        execute = liquidity_ok and spread_ok
        return TradeFilterDecision(
            execute=execute,
            confidence_score=7.0 if execute else 3.5,
            size_modifier=1.0 if execute else 0.5,
            reasoning="Phase 1 scaffold result. Phase 4 will add AI-assisted trade filtering.",
        )
