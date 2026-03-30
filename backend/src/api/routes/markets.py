from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.core.database import get_db
from backend.src.models.market import Market, MarketOutcome, MarketStatus

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("")
async def list_markets(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    min_volume: Optional[float] = None,
    min_ai_score: Optional[float] = None,
    category: Optional[str] = None,
    sort_by: str = Query(default="ai_score", regex="^(ai_score|volume_24h|liquidity|created_at)$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Market).where(
        Market.is_active == True,
        Market.status == MarketStatus.ACTIVE,
    )

    if min_volume:
        query = query.where(Market.volume >= min_volume)
    if min_ai_score:
        query = query.where(Market.ai_score >= min_ai_score)
    if category:
        query = query.where(Market.category == category)

    sort_col = getattr(Market, sort_by)
    query = query.order_by(sort_col.desc().nulls_last())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query.options(selectinload(Market.outcomes)))
    markets = result.scalars().all()

    return {
        "markets": [
            {
                "id": m.id,
                "condition_id": m.condition_id,
                "question": m.question,
                "category": m.category,
                "status": m.status,
                "volume": m.volume,
                "volume_24h": m.volume_24h,
                "liquidity": m.liquidity,
                "spread": m.spread,
                "ai_score": m.ai_score,
                "ai_reasoning": m.ai_reasoning,
                "ai_tags": m.ai_tags.split(",") if m.ai_tags else [],
                "ai_scored_at": str(m.ai_scored_at) if m.ai_scored_at else None,
                "outcomes": [
                    {
                        "token_id": o.token_id,
                        "outcome": o.outcome,
                        "price": o.price,
                    }
                    for o in m.outcomes
                ],
                "source_url": m.source_url,
                "created_at": str(m.created_at),
            }
            for m in markets
        ],
        "total": len(markets),
        "offset": offset,
        "limit": limit,
    }


@router.get("/{market_id}")
async def get_market(market_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Market)
        .where(Market.id == market_id)
        .options(selectinload(Market.outcomes))
    )
    market = result.scalar_one_or_none()
    if not market:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Market not found")

    return {
        "id": market.id,
        "condition_id": market.condition_id,
        "question": market.question,
        "description": market.description,
        "category": market.category,
        "status": market.status,
        "volume": market.volume,
        "volume_24h": market.volume_24h,
        "liquidity": market.liquidity,
        "spread": market.spread,
        "ai_score": market.ai_score,
        "ai_reasoning": market.ai_reasoning,
        "ai_tags": market.ai_tags.split(",") if market.ai_tags else [],
        "outcomes": [
            {"token_id": o.token_id, "outcome": o.outcome, "price": o.price}
            for o in market.outcomes
        ],
        "source_url": market.source_url,
    }


@router.post("/discover")
async def trigger_discovery(
    limit: int = Query(default=50, le=200),
    with_ai: bool = True,
) -> dict:
    from backend.src.services.market_discovery import MarketDiscoveryService

    service = MarketDiscoveryService()
    markets = await service.discover_markets(limit=limit, with_ai_scoring=with_ai)
    return {
        "discovered": len(markets),
        "message": f"Discovered {len(markets)} markets" + (" with AI scoring" if with_ai else ""),
    }
