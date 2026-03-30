from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db
from backend.src.models.position import Position

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
async def list_positions(
    open_only: bool = True,
    strategy: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Position).order_by(Position.created_at.desc())

    if open_only:
        query = query.where(Position.is_open == True)
    if strategy:
        query = query.where(Position.strategy == strategy)

    result = await db.execute(query)
    positions = result.scalars().all()

    total_unrealized = sum(p.unrealized_pnl for p in positions)
    total_realized = sum(p.realized_pnl for p in positions)

    return {
        "positions": [
            {
                "id": p.id,
                "condition_id": p.condition_id,
                "outcome": p.outcome,
                "side": p.side,
                "size": p.size,
                "avg_entry_price": p.avg_entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "realized_pnl": p.realized_pnl,
                "strategy": p.strategy,
                "is_paper": p.is_paper,
                "is_open": p.is_open,
                "stop_loss": p.stop_loss,
                "take_profit": p.take_profit,
                "created_at": str(p.created_at),
            }
            for p in positions
        ],
        "total_unrealized_pnl": total_unrealized,
        "total_realized_pnl": total_realized,
        "open_count": len([p for p in positions if p.is_open]),
    }
