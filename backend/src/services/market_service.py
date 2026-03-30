"""
Market Service — discovery, ingestion, AI scoring, and storage.

Phase 1: Market discovery + AI scoring scaffold
Phase 2: Live updates + WebSocket integration
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import db_session
from src.core.logging import get_logger
from src.data.polymarket_client import get_polymarket_client, PolymarketClient
from src.models.market import Market
from src.ai.scoring import score_market, score_markets_batch, passes_hard_filter

logger = get_logger(__name__)


class MarketService:

    def __init__(self, client: Optional[PolymarketClient] = None):
        self._client = client or get_polymarket_client()

    async def discover_and_score_markets(
        self,
        limit: int = 100,
        min_volume: float = 1000,
        score_with_ai: bool = True,
    ) -> Dict[str, Any]:
        """
        Full market discovery pipeline:
        1. Fetch from Polymarket API
        2. Apply hard filters (deterministic)
        3. Upsert to database
        4. Score with AI (batch, async)

        Returns summary stats.
        """
        logger.info("market_discovery_started", limit=limit, min_volume=min_volume)

        raw_markets = await self._client.get_markets(limit=limit, min_volume=min_volume)
        logger.info("markets_fetched", count=len(raw_markets))

        normalized = [self._client.normalize_market(m) for m in raw_markets]

        # Hard filter (deterministic — always runs before AI)
        filtered = []
        filter_stats = {}
        for m in normalized:
            passes, reason = passes_hard_filter(m)
            if passes:
                filtered.append(m)
            else:
                filter_stats[reason] = filter_stats.get(reason, 0) + 1

        logger.info("markets_after_filter", passed=len(filtered), rejected=len(normalized) - len(filtered), stats=filter_stats)

        # Upsert to DB
        saved_ids = await self._upsert_markets(filtered)

        # AI scoring (async batch — does not block storage)
        if score_with_ai and filtered:
            asyncio.create_task(self._score_markets_background(filtered, saved_ids))

        return {
            "fetched": len(raw_markets),
            "after_filter": len(filtered),
            "filter_rejections": filter_stats,
            "saved": len(saved_ids),
            "ai_scoring_queued": score_with_ai,
        }

    async def _upsert_markets(self, markets: List[Dict[str, Any]]) -> Dict[str, str]:
        """Upsert markets to database. Returns condition_id → db_id mapping."""
        id_map = {}

        async with db_session() as session:
            for m in markets:
                existing = await session.execute(
                    select(Market).where(Market.condition_id == m["condition_id"])
                )
                existing = existing.scalar_one_or_none()

                if existing:
                    # Update price/volume data
                    for field in ["best_bid", "best_ask", "mid_price", "spread", "spread_pct",
                                  "volume_24h", "volume_total", "liquidity", "open_interest",
                                  "active", "closed", "accepting_orders"]:
                        if m.get(field) is not None:
                            setattr(existing, field, m[field])
                    id_map[m["condition_id"]] = existing.id
                else:
                    market_obj = Market(
                        condition_id=m["condition_id"],
                        question_id=m.get("question_id"),
                        slug=m.get("slug"),
                        question=m["question"],
                        description=m.get("description"),
                        category=m.get("category"),
                        best_bid=m.get("best_bid"),
                        best_ask=m.get("best_ask"),
                        mid_price=m.get("mid_price"),
                        spread=m.get("spread"),
                        spread_pct=m.get("spread_pct"),
                        volume_24h=m.get("volume_24h", 0),
                        volume_total=m.get("volume_total", 0),
                        liquidity=m.get("liquidity", 0),
                        open_interest=m.get("open_interest", 0),
                        active=m.get("active", True),
                        closed=m.get("closed", False),
                        accepting_orders=m.get("accepting_orders", True),
                        end_date=m.get("end_date"),
                    )
                    session.add(market_obj)
                    await session.flush()
                    id_map[m["condition_id"]] = market_obj.id

        logger.info("markets_upserted", count=len(id_map))
        return id_map

    async def _score_markets_background(
        self,
        markets: List[Dict[str, Any]],
        id_map: Dict[str, str],
    ) -> None:
        """Run AI scoring in background, update DB with scores."""
        logger.info("ai_scoring_background_started", count=len(markets))

        try:
            scores = await score_markets_batch(markets)

            async with db_session() as session:
                for market_data, score_result in zip(markets, scores):
                    condition_id = market_data["condition_id"]
                    db_id = id_map.get(condition_id)
                    if not db_id or not score_result:
                        continue

                    import json
                    await session.execute(
                        update(Market)
                        .where(Market.condition_id == condition_id)
                        .values(
                            ai_score=score_result.get("score"),
                            ai_reasoning=score_result.get("reasoning"),
                            ai_tags=json.dumps(score_result.get("tags", [])),
                            ai_scored_at=datetime.now(timezone.utc),
                        )
                    )

            logger.info("ai_scoring_background_completed", count=len(markets))
        except Exception as e:
            logger.error("ai_scoring_background_failed", error=str(e))

    async def get_scored_markets(
        self,
        session: AsyncSession,
        min_score: float = 0.0,
        limit: int = 50,
        category: Optional[str] = None,
    ) -> List[Market]:
        """Fetch markets from DB, sorted by AI score."""
        query = (
            select(Market)
            .where(Market.active == True, Market.closed == False)
        )
        if min_score > 0:
            query = query.where(Market.ai_score >= min_score)
        if category:
            query = query.where(Market.category == category)

        query = query.order_by(Market.ai_score.desc().nullslast()).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def refresh_market_prices(self, condition_ids: List[str]) -> int:
        """Pull fresh price data for a set of markets."""
        updated = 0
        for condition_id in condition_ids:
            raw = await self._client.get_market(condition_id)
            if not raw:
                continue

            normalized = self._client.normalize_market(raw)
            async with db_session() as session:
                await session.execute(
                    update(Market)
                    .where(Market.condition_id == condition_id)
                    .values(
                        best_bid=normalized.get("best_bid"),
                        best_ask=normalized.get("best_ask"),
                        spread_pct=normalized.get("spread_pct"),
                        volume_24h=normalized.get("volume_24h"),
                        liquidity=normalized.get("liquidity"),
                    )
                )
            updated += 1

        return updated
