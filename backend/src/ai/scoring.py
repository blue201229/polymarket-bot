from __future__ import annotations

from ai.ai_engine import AIEngine
from app.domain.models import AIScore, MarketSnapshot


class MarketScoringService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine

    async def score_markets(self, markets: list[MarketSnapshot]) -> list[AIScore]:
        payloads = [self._to_payload(market) for market in markets]
        return await self.ai_engine.evaluate_batch(
            "market_prompt.txt",
            payloads,
            self._fallback_score,
            decision_impact="market prioritization only",
        )

    def _to_payload(self, market: MarketSnapshot) -> dict:
        return {
            "market_id": market.market_id,
            "question": market.question,
            "category": market.category,
            "liquidity": market.liquidity,
            "volume_24h": market.volume_24h,
            "spread_bps": market.spread_bps,
            "resolution_clarity": market.resolution_clarity,
            "hype_score": market.metadata.get("hype_score", 0.5),
            "news_density": market.metadata.get("news_density", 0.5),
        }

    def _fallback_score(self, payload: dict, source: str) -> AIScore:
        clarity = float(payload.get("resolution_clarity", 0.5))
        score = round(4.0 + clarity * 3.0, 2)
        return AIScore(
            source=source,
            score=min(score, 10.0),
            reasoning="Fallback heuristic score based on deterministic market clarity.",
            tags=["fallback", "deterministic-assist"],
            decision_impact="market prioritization only",
        )
