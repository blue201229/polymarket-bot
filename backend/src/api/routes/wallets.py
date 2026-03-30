from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/wallets", tags=["wallets"])


class AddWalletRequest(BaseModel):
    address: str
    label: Optional[str] = None
    copy_enabled: bool = False
    copy_size_multiplier: float = 1.0


@router.get("")
async def list_wallets() -> dict:
    from backend.src.services.wallet_watcher import WalletWatcher

    watcher = WalletWatcher()
    wallets = await watcher.get_all_wallets()
    return {"wallets": wallets, "total": len(wallets)}


@router.post("")
async def add_wallet(req: AddWalletRequest) -> dict:
    from backend.src.services.wallet_watcher import WalletWatcher

    watcher = WalletWatcher()
    wallet = await watcher.add_wallet(
        address=req.address,
        label=req.label,
        copy_enabled=req.copy_enabled,
        copy_size_multiplier=req.copy_size_multiplier,
    )
    return {
        "address": wallet.address,
        "label": wallet.label,
        "copy_enabled": wallet.copy_enabled,
        "message": "Wallet added successfully",
    }


@router.delete("/{address}")
async def remove_wallet(address: str) -> dict:
    from backend.src.services.wallet_watcher import WalletWatcher

    watcher = WalletWatcher()
    await watcher.remove_wallet(address)
    return {"message": f"Wallet {address[:10]}... deactivated"}


@router.post("/{address}/analyze")
async def analyze_wallet(address: str) -> dict:
    from backend.src.services.wallet_watcher import WalletWatcher

    watcher = WalletWatcher()
    profile = await watcher.analyze_wallet(address)
    if profile is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "address": address,
        "quality_score": profile.quality_score,
        "strategy_classification": profile.strategy_classification,
        "confidence": profile.confidence,
        "risk_profile": profile.risk_profile,
        "copy_recommendation": profile.copy_recommendation,
        "reasoning": profile.reasoning,
        "strengths": profile.strengths,
        "weaknesses": profile.weaknesses,
    }
