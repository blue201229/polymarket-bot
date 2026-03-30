from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from ai.ai_engine import AIEngine
from ai.scoring import MarketScoringService
from app.core.config import get_settings
from app.domain.models import (
    HardFilterDecision,
    MarketCandidate,
    MarketDiscoveryResponse,
    MarketSnapshot,
    sample_end_time,
)


class MarketDiscoveryService:
    def __init__(self, ai_engine: AIEngine) -> None:
        self.ai_engine = ai_engine
        self.market_scorer = MarketScoringService(ai_engine)

    async def discover_markets(self, ai_enabled: bool, limit: int) -> MarketDiscoveryResponse:
        snapshots = self._seed_markets()
        candidates: list[MarketCandidate] = []

        for market in snapshots:
            hard_filter = self._apply_hard_filters(market)
            deterministic_priority = round(hard_filter.deterministic_score, 2)
            candidate = MarketCandidate(
                market=market,
                hard_filter=hard_filter,
                deterministic_priority=deterministic_priority,
                priority_score=deterministic_priority,
            )
            candidates.append(candidate)

        passed = [candidate for candidate in candidates if candidate.hard_filter.passed]
        if ai_enabled and passed:
            ai_scores = await self.market_scorer.score_markets([candidate.market for candidate in passed])
            for candidate, ai_score in zip(passed, ai_scores, strict=True):
                candidate.ai_score = ai_score
                candidate.priority_score = round(
                    min(10.0, candidate.deterministic_priority * 0.65 + ai_score.score * 0.35),
                    2,
                )

        ordered = sorted(candidates, key=lambda item: item.priority_score, reverse=True)
        return MarketDiscoveryResponse(
            generated_at=datetime.now(timezone.utc),
            ai_enabled=ai_enabled,
            candidates=ordered[:limit],
        )

    def _apply_hard_filters(self, market: MarketSnapshot) -> HardFilterDecision:
        reasons: list[str] = []
        if market.liquidity < 15_000:
            reasons.append("insufficient liquidity")
        if market.spread_bps > 220:
            reasons.append("spread too wide")
        if market.resolution_clarity < 0.6:
            reasons.append("resolution unclear")

        passed = not reasons
        liquidity_component = min(market.liquidity / 50_000, 1.0) * 3.5
        volume_component = min(market.volume_24h / 60_000, 1.0) * 3.0
        clarity_component = market.resolution_clarity * 2.0
        spread_component = max(0.0, 1.5 - (market.spread_bps / 200))
        score = round(liquidity_component + volume_component + clarity_component + spread_component, 2)
        if not passed:
            score = max(0.0, round(score - 2.0, 2))

        return HardFilterDecision(
            passed=passed,
            reasons=reasons or ["passed deterministic filters"],
            deterministic_score=min(score, 10.0),
        )

    def _seed_markets(self) -> list[MarketSnapshot]:
        return [
            MarketSnapshot(
                market_id="pm-001",
                question="Will the SEC approve a spot ETF proposal before Q3?",
                category="regulation",
                liquidity=54_200,
                volume_24h=62_500,
                spread_bps=88,
                resolution_clarity=0.93,
                end_time=sample_end_time(45),
                metadata={"hype_score": 0.72, "news_density": 0.81},
            ),
            MarketSnapshot(
                market_id="pm-002",
                question="Will BTC trade above 95k by month-end?",
                category="crypto",
                liquidity=49_500,
                volume_24h=73_100,
                spread_bps=64,
                resolution_clarity=0.97,
                end_time=sample_end_time(12),
                metadata={"hype_score": 0.88, "news_density": 0.67},
            ),
            MarketSnapshot(
                market_id="pm-003",
                question="Will Candidate A win the primary debate?",
                category="politics",
                liquidity=11_000,
                volume_24h=14_200,
                spread_bps=190,
                resolution_clarity=0.58,
                end_time=sample_end_time(18),
                metadata={"hype_score": 0.91, "news_density": 0.75},
            ),
            MarketSnapshot(
                market_id="pm-004",
                question="Will Ethereum Layer-2 TVL exceed 50B this quarter?",
                category="crypto",
                liquidity=18_900,
                volume_24h=22_600,
                spread_bps=245,
                resolution_clarity=0.82,
                end_time=sample_end_time(26),
                metadata={"hype_score": 0.55, "news_density": 0.46},
            ),
            MarketSnapshot(
                market_id="pm-005",
                question="Will the Fed cut rates at the next meeting?",
                category="macro",
                liquidity=65_000,
                volume_24h=59_300,
                spread_bps=105,
                resolution_clarity=0.9,
                end_time=sample_end_time(21),
                metadata={"hype_score": 0.62, "news_density": 0.84},
            ),
        ]


@lru_cache(maxsize=1)
def get_market_discovery_service() -> MarketDiscoveryService:
    settings = get_settings()
    ai_engine = AIEngine.from_settings(settings)
    return MarketDiscoveryService(ai_engine=ai_engine)
