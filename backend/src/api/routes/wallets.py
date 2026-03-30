"""Wallets API routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.wallet import Wallet, WalletTrade
from src.api.schemas import AddWalletRequest, WalletResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("", response_model=List[WalletResponse])
async def list_wallets(
    tracked_only: bool = True,
    min_score: float = Query(0.0, ge=0, le=10),
    db: AsyncSession = Depends(get_db),
):
    query = select(Wallet)
    if tracked_only:
        query = query.where(Wallet.is_tracked == True)
    if min_score > 0:
        query = query.where(Wallet.ai_quality_score >= min_score)

    query = query.order_by(Wallet.ai_quality_score.desc().nullslast())
    wallets = list((await db.execute(query)).scalars().all())
    return wallets


@router.post("", response_model=WalletResponse)
async def add_wallet(req: AddWalletRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(
        select(Wallet).where(Wallet.address == req.address)
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Wallet already tracked")

    wallet = Wallet(
        address=req.address,
        label=req.label,
        copy_trade_enabled=req.copy_trade_enabled,
        copy_trade_max_size_usdc=req.copy_trade_max_size_usdc,
        copy_trade_size_pct=req.copy_trade_size_pct,
    )
    db.add(wallet)
    await db.flush()
    return wallet


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(wallet_id: str, db: AsyncSession = Depends(get_db)):
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.delete("/{wallet_id}")
async def remove_wallet(wallet_id: str, db: AsyncSession = Depends(get_db)):
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    wallet.is_tracked = False
    return {"status": "removed"}


@router.get("/{wallet_id}/trades")
async def get_wallet_trades(
    wallet_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    trades = list((await db.execute(
        select(WalletTrade)
        .where(WalletTrade.wallet_id == wallet_id)
        .order_by(WalletTrade.timestamp.desc())
        .limit(limit)
    )).scalars().all())

    return [
        {
            "condition_id": t.condition_id,
            "side": t.side,
            "outcome": t.outcome,
            "price": t.price,
            "size": t.size,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
        }
        for t in trades
    ]
