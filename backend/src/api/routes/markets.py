"""Markets API routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.market import Market
from src.api.schemas import MarketListResponse, MarketResponse
from src.services.market_service import MarketService
from src.ai.scoring import score_market, passes_hard_filter
from src.api.schemas import MarketScoreRequest, MarketScoreResponse

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=MarketListResponse)
async def list_markets(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.0, ge=0, le=10),
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    query = select(Market)

    if active_only:
        query = query.where(Market.active == True, Market.closed == False)
    if min_score > 0:
        query = query.where(Market.ai_score >= min_score)
    if category:
        query = query.where(Market.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Market.ai_score.desc().nullslast()).offset(offset).limit(limit)
    markets = list((await db.execute(query)).scalars().all())

    return MarketListResponse(
        markets=markets,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{condition_id}", response_model=MarketResponse)
async def get_market(condition_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).where(Market.condition_id == condition_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@router.post("/discover")
async def trigger_discovery(
    limit: int = Query(100, ge=1, le=500),
    min_volume: float = Query(1000, ge=0),
):
    """Trigger market discovery + AI scoring pipeline."""
    service = MarketService()
    result = await service.discover_and_score_markets(limit=limit, min_volume=min_volume)
    return result


@router.post("/score", response_model=MarketScoreResponse)
async def score_market_endpoint(
    req: MarketScoreRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request AI scoring for a specific market."""
    result = await db.execute(
        select(Market).where(Market.condition_id == req.condition_id)
    )
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    passes, reason = passes_hard_filter({
        "liquidity": market.liquidity,
        "spread_pct": market.spread_pct or 1.0,
        "volume_24h": market.volume_24h,
    })

    if not passes:
        raise HTTPException(status_code=400, detail=f"Market fails hard filter: {reason}")

    market_data = {
        "id": market.id,
        "question": market.question,
        "description": market.description or "",
        "category": market.category or "",
        "end_date": market.end_date.isoformat() if market.end_date else None,
        "best_bid": market.best_bid,
        "best_ask": market.best_ask,
        "spread_pct": market.spread_pct,
        "volume_24h": market.volume_24h,
        "liquidity": market.liquidity,
        "open_interest": market.open_interest,
    }

    score = await score_market(market_data, market_id=market.id)

    import json
    from datetime import datetime, timezone
    from sqlalchemy import update
    await db.execute(
        update(Market).where(Market.condition_id == req.condition_id).values(
            ai_score=score.get("score"),
            ai_reasoning=score.get("reasoning"),
            ai_tags=json.dumps(score.get("tags", [])),
            ai_scored_at=datetime.now(timezone.utc),
        )
    )

    tags = score.get("tags", [])
    if isinstance(tags, str):
        import json as _json
        try:
            tags = _json.loads(tags)
        except Exception:
            tags = []

    return MarketScoreResponse(
        condition_id=req.condition_id,
        score=score.get("score", 0),
        reasoning=score.get("reasoning", ""),
        tags=tags,
        volatility_potential=score.get("volatility_potential", "unknown"),
        resolution_clarity=score.get("resolution_clarity", "unknown"),
        recommended_action=score.get("recommended_action", "monitor"),
        key_risk=score.get("key_risk", ""),
        is_fallback=score.get("_fallback", False),
        cache_hit=score.get("_cache_hit", False),
    )
