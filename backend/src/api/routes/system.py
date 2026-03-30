"""System routes — health, risk params, settings."""
from fastapi import APIRouter, HTTPException

from src.core.config import settings
from src.api.schemas import (
    HealthResponse,
    RiskParamsResponse,
    UpdateRiskParamsRequest,
)
from src.services.risk_engine import get_risk_engine, get_risk_params, update_risk_params

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        paper_trading=settings.paper_trading_mode,
        ai_enabled=settings.ai_enabled,
        ai_available=settings.ai_available,
    )


@router.get("/risk", response_model=RiskParamsResponse)
async def get_risk():
    params = get_risk_params()
    return RiskParamsResponse(
        max_position_size_usdc=params.max_position_size_usdc,
        max_total_exposure_usdc=params.max_total_exposure_usdc,
        max_positions=params.max_positions,
        min_liquidity=params.min_liquidity,
        max_spread_pct=params.max_spread_pct,
        max_slippage_pct=params.max_slippage_pct,
        paper_trading=params.paper_trading,
        trading_paused=params.trading_paused,
        pause_reason=params.pause_reason,
    )


@router.put("/risk", response_model=RiskParamsResponse)
async def update_risk(req: UpdateRiskParamsRequest):
    """Update risk parameters. Requires explicit operator action."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No parameters to update")

    params = update_risk_params(updates)
    return RiskParamsResponse(
        max_position_size_usdc=params.max_position_size_usdc,
        max_total_exposure_usdc=params.max_total_exposure_usdc,
        max_positions=params.max_positions,
        min_liquidity=params.min_liquidity,
        max_spread_pct=params.max_spread_pct,
        max_slippage_pct=params.max_slippage_pct,
        paper_trading=params.paper_trading,
        trading_paused=params.trading_paused,
        pause_reason=params.pause_reason,
    )


@router.post("/trading/pause")
async def pause_trading(reason: str = "operator_request"):
    """Pause all new trade entries."""
    get_risk_engine().pause_trading(reason)
    return {"status": "paused", "reason": reason}


@router.post("/trading/resume")
async def resume_trading():
    """Resume trading after pause."""
    get_risk_engine().resume_trading()
    return {"status": "resumed"}
