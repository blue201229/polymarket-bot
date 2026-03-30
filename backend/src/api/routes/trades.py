from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db
from backend.src.models.trade import Trade, TradeStatus

router = APIRouter(prefix="/trades", tags=["trades"])


class TradeSignalRequest(BaseModel):
    condition_id: str
    token_id: str
    outcome: str
    side: str
    price: float
    size: float
    strategy: str = "manual"
    skip_ai: bool = False


@router.get("")
async def list_trades(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    strategy: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Trade).order_by(Trade.created_at.desc())

    if strategy:
        query = query.where(Trade.strategy == strategy)
    if status:
        query = query.where(Trade.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    trades = result.scalars().all()

    return {
        "trades": [
            {
                "id": t.id,
                "condition_id": t.condition_id,
                "outcome": t.outcome,
                "side": t.side,
                "status": t.status,
                "price": t.price,
                "size": t.size,
                "filled_size": t.filled_size,
                "filled_price": t.filled_price,
                "strategy": t.strategy,
                "is_paper": t.is_paper,
                "ai_confidence": t.ai_confidence,
                "ai_size_modifier": t.ai_size_modifier,
                "ai_approved": t.ai_approved,
                "ai_skip_reason": t.ai_skip_reason,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "created_at": str(t.created_at),
                "closed_at": str(t.closed_at) if t.closed_at else None,
            }
            for t in trades
        ],
        "total": len(trades),
    }


@router.post("/signal")
async def submit_signal(req: TradeSignalRequest) -> dict:
    from backend.src.services.execution_engine import ExecutionEngine

    engine = ExecutionEngine()
    trade = await engine.execute_signal(
        market_id="",
        condition_id=req.condition_id,
        token_id=req.token_id,
        outcome=req.outcome,
        side=req.side,
        price=req.price,
        size=req.size,
        strategy=req.strategy,
        skip_ai=req.skip_ai,
    )

    if trade is None:
        return {"status": "rejected", "reason": "Trade could not be processed"}

    return {
        "status": trade.status,
        "trade_id": trade.id,
        "ai_confidence": trade.ai_confidence,
        "ai_approved": trade.ai_approved,
        "size": trade.size,
        "price": trade.price,
    }


@router.get("/stats")
async def trade_stats(db: AsyncSession = Depends(get_db)) -> dict:
    total = await db.execute(select(func.count(Trade.id)))
    filled = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.status.in_([TradeStatus.FILLED, TradeStatus.PAPER])
        )
    )
    cancelled = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.CANCELLED)
    )
    total_pnl = await db.execute(
        select(func.coalesce(func.sum(Trade.pnl), 0)).where(
            Trade.status.in_([TradeStatus.FILLED, TradeStatus.PAPER])
        )
    )

    return {
        "total_trades": total.scalar() or 0,
        "filled_trades": filled.scalar() or 0,
        "cancelled_trades": cancelled.scalar() or 0,
        "total_pnl": float(total_pnl.scalar() or 0),
    }
