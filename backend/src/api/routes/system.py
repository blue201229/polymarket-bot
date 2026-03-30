from __future__ import annotations

from fastapi import APIRouter

from backend.src.config import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "environment": settings.environment.value,
        "paper_trading": settings.paper_trading,
        "ai_enabled": settings.ai_enabled,
    }


@router.get("/config")
async def get_config() -> dict:
    return {
        "environment": settings.environment.value,
        "paper_trading": settings.paper_trading,
        "ai_enabled": settings.ai_enabled,
        "ai_provider": settings.ai_default_provider,
        "ai_model": settings.ai_default_model,
        "ai_timeout": settings.ai_timeout_seconds,
        "max_position_size_usd": settings.max_position_size_usd,
        "max_daily_loss_usd": settings.max_daily_loss_usd,
        "max_open_positions": settings.max_open_positions,
        "default_slippage_bps": settings.default_slippage_bps,
    }
