"""Trades API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models.market import Market
from src.models.trade import Trade
from src.api.schemas import ManualTradeRequest, TradeListResponse, TradeResponse
from src.services.execution_engine import get_execution_engine, TradeRequest

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=TradeListResponse)
async def list_trades(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    is_paper: Optional[bool] = None,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    query = select(Trade)

    if status:
        query = query.where(Trade.status == status)
    if is_paper is not None:
        query = query.where(Trade.is_paper == is_paper)
    if source:
        query = query.where(Trade.source == source)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Trade.created_at.desc()).offset(offset).limit(limit)
    trades = list((await db.execute(query)).scalars().all())

    return TradeListResponse(trades=trades, total=total)


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: str, db: AsyncSession = Depends(get_db)):
    trade = await db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("", response_model=TradeResponse)
async def place_manual_trade(
    req: ManualTradeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Place a manual trade through the full pipeline (risk engine + AI filter)."""
    market = (await db.execute(
        select(Market).where(Market.condition_id == req.condition_id)
    )).scalar_one_or_none()

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    if not market.active or market.closed:
        raise HTTPException(status_code=400, detail="Market is not active")

    engine = get_execution_engine()
    trade_request = TradeRequest(
        condition_id=req.condition_id,
        market_id=market.id,
        side=req.side,
        outcome=req.outcome,
        source="manual",
        size_usdc=req.size_usdc,
        target_price=req.target_price,
        max_slippage_pct=req.max_slippage_pct,
    )

    trade = await engine.execute(
        trade_request,
        market_liquidity=market.liquidity,
        market_spread_pct=market.spread_pct or 0.1,
        current_positions_count=0,  # TODO: query live count
        current_total_exposure_usdc=0.0,  # TODO: query live exposure
    )

    return trade


@router.get("/stats/summary")
async def get_trade_stats(
    is_paper: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Trade performance summary."""
    query = select(Trade)
    if is_paper is not None:
        query = query.where(Trade.is_paper == is_paper)

    trades = list((await db.execute(query)).scalars().all())
    filled = [t for t in trades if t.status == "filled"]
    rejected = [t for t in trades if t.status == "risk_rejected"]
    ai_skipped = [t for t in trades if t.status == "ai_skipped"]

    pnl_trades = [t for t in filled if t.pnl_usdc is not None]
    total_pnl = sum(t.pnl_usdc for t in pnl_trades)
    wins = [t for t in pnl_trades if t.pnl_usdc > 0]

    return {
        "total_trades": len(trades),
        "filled": len(filled),
        "risk_rejected": len(rejected),
        "ai_skipped": len(ai_skipped),
        "total_pnl_usdc": round(total_pnl, 4),
        "win_rate": round(len(wins) / len(pnl_trades), 3) if pnl_trades else None,
        "paper_trading": settings.paper_trading_mode,
    }
