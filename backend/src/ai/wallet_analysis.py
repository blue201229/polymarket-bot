from __future__ import annotations

from ai.ai_engine import AIEngine
from app.domain.models import WalletAnalysisResult


class WalletAnalysisService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine

    async def analyze_wallet(self, wallet: str, features: dict) -> WalletAnalysisResult:
        activity = float(features.get("activity_score", 0.5))
        return WalletAnalysisResult(
            wallet=wallet,
            quality_score=round(min(10.0, 4.5 + activity * 4.0), 2),
            strategy_classification="unclassified",
            confidence=0.35,
            reasoning="Phase 1 scaffold result. Phase 3 will add AI-backed wallet profiling.",
        )
