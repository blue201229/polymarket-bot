from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.ai.scoring import MarketScore, MarketScorer
from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger
from backend.src.models.market import Market, MarketOutcome, MarketStatus
from backend.src.utils.http_client import http_get

logger = get_logger("services.market_discovery")


class MarketFilters:
    """Deterministic hard filters applied BEFORE AI scoring."""

    def __init__(
        self,
        min_volume: float = 1000.0,
        min_liquidity: float = 500.0,
        min_volume_24h: float = 100.0,
        max_spread_bps: int = 500,
        exclude_resolved: bool = True,
    ):
        self.min_volume = min_volume
        self.min_liquidity = min_liquidity
        self.min_volume_24h = min_volume_24h
        self.max_spread_bps = max_spread_bps
        self.exclude_resolved = exclude_resolved

    def passes(self, market_data: dict[str, Any]) -> tuple[bool, str]:
        volume = float(market_data.get("volume", 0))
        if volume < self.min_volume:
            return False, f"volume {volume} < {self.min_volume}"

        liquidity = float(market_data.get("liquidity", 0))
        if liquidity < self.min_liquidity:
            return False, f"liquidity {liquidity} < {self.min_liquidity}"

        if self.exclude_resolved and market_data.get("closed", False):
            return False, "market is closed/resolved"

        return True, "passed"


class MarketDiscoveryService:
    """
    Discovers and indexes markets from Polymarket APIs.

    Pipeline:
    1. Fetch markets from Gamma API
    2. Apply deterministic hard filters
    3. (Optional) AI scoring for prioritization
    4. Store/update in database
    5. Publish events for downstream consumers
    """

    def __init__(self, scorer: Optional[MarketScorer] = None) -> None:
        self._filters = MarketFilters()
        self._scorer = scorer or MarketScorer()
        self._gamma_url = settings.polymarket_gamma_url

    async def discover_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        with_ai_scoring: bool = True,
    ) -> list[dict[str, Any]]:
        try:
            raw_markets = await self._fetch_from_gamma(limit=limit, offset=offset)
        except Exception as e:
            logger.error("Failed to fetch markets from Gamma API", error=str(e))
            return []

        passed_markets = []
        for m in raw_markets:
            market_data = self._normalize_gamma_market(m)
            ok, reason = self._filters.passes(market_data)
            if ok:
                passed_markets.append(market_data)
            else:
                logger.debug("Market filtered out", question=market_data.get("question", "")[:50],
                           reason=reason)

        logger.info(
            "Market discovery results",
            fetched=len(raw_markets),
            passed_filters=len(passed_markets),
        )

        if with_ai_scoring and passed_markets and settings.ai_enabled:
            scores = await self._scorer.score_markets_batch(passed_markets)
            for market_data, score in zip(passed_markets, scores):
                market_data["ai_score"] = score.score
                market_data["ai_reasoning"] = score.reasoning
                market_data["ai_tags"] = ",".join(score.tags)
                market_data["ai_suggested_action"] = score.suggested_action

        stored = await self._store_markets(passed_markets)

        for m in stored:
            await event_bus.publish(Events.MARKET_DISCOVERED, market=m)

        return passed_markets

    async def _fetch_from_gamma(self, limit: int = 100, offset: int = 0) -> list[dict]:
        url = f"{self._gamma_url}/markets"
        params = {
            "limit": limit,
            "offset": offset,
            "active": True,
            "closed": False,
        }
        return await http_get(url, params=params)

    def _normalize_gamma_market(self, raw: dict) -> dict[str, Any]:
        outcomes = []
        tokens = raw.get("tokens", []) or []
        for token in tokens:
            outcomes.append({
                "token_id": token.get("token_id", ""),
                "outcome": token.get("outcome", ""),
                "price": float(token.get("price", 0)),
            })

        prices = [o["price"] for o in outcomes if o["price"] > 0]
        spread = None
        if len(prices) >= 2:
            spread = abs(prices[0] - prices[1])

        return {
            "condition_id": raw.get("condition_id", ""),
            "question": raw.get("question", ""),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "end_date": raw.get("end_date_iso"),
            "volume": float(raw.get("volume", 0)),
            "volume_24h": float(raw.get("volume_num_24hr", 0) or 0),
            "liquidity": float(raw.get("liquidity", 0) or 0),
            "spread": spread,
            "outcomes": outcomes,
            "slug": raw.get("slug", ""),
            "source_url": f"https://polymarket.com/event/{raw.get('slug', '')}",
            "closed": raw.get("closed", False),
            "active": raw.get("active", True),
        }

    async def _store_markets(self, markets: list[dict[str, Any]]) -> list[dict]:
        stored = []
        async with get_session() as session:
            for m in markets:
                condition_id = m.get("condition_id", "")
                if not condition_id:
                    continue

                result = await session.execute(
                    select(Market).where(Market.condition_id == condition_id)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.volume = m.get("volume", 0)
                    existing.volume_24h = m.get("volume_24h", 0)
                    existing.liquidity = m.get("liquidity", 0)
                    existing.spread = m.get("spread")
                    if m.get("ai_score") is not None:
                        existing.ai_score = m["ai_score"]
                        existing.ai_reasoning = m.get("ai_reasoning")
                        existing.ai_tags = m.get("ai_tags")
                        existing.ai_scored_at = datetime.now(timezone.utc)
                    stored.append(m)
                else:
                    market = Market(
                        condition_id=condition_id,
                        question=m.get("question", ""),
                        description=m.get("description"),
                        category=m.get("category"),
                        end_date=None,
                        volume=m.get("volume", 0),
                        volume_24h=m.get("volume_24h", 0),
                        liquidity=m.get("liquidity", 0),
                        spread=m.get("spread"),
                        ai_score=m.get("ai_score"),
                        ai_reasoning=m.get("ai_reasoning"),
                        ai_tags=m.get("ai_tags"),
                        ai_scored_at=(
                            datetime.now(timezone.utc) if m.get("ai_score") is not None else None
                        ),
                        slug=m.get("slug"),
                        source_url=m.get("source_url"),
                    )
                    session.add(market)

                    for o in m.get("outcomes", []):
                        outcome = MarketOutcome(
                            market_id=market.id,
                            token_id=o.get("token_id", ""),
                            outcome=o.get("outcome", ""),
                            price=o.get("price", 0),
                        )
                        session.add(outcome)
                    stored.append(m)

        return stored

    async def get_top_markets(
        self,
        session: AsyncSession,
        limit: int = 20,
        min_ai_score: Optional[float] = None,
    ) -> list[Market]:
        query = select(Market).where(
            Market.is_active == True,
            Market.status == MarketStatus.ACTIVE,
        )
        if min_ai_score is not None:
            query = query.where(Market.ai_score >= min_ai_score)
        query = query.order_by(Market.ai_score.desc().nulls_last(), Market.volume_24h.desc())
        query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())
