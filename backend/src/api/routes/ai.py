"""AI API routes — expose AI capabilities to frontends."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.models.ai_log import AILog
from src.models.market import Market
from src.api.schemas import (
    TradeFilterRequest,
    TradeFilterResponse,
    OptimizationResponse,
)
from src.ai.trade_filter import filter_signal
from src.ai.optimizer import suggest_optimizations
from src.ai.anomaly_detector import detect_market_anomalies

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
async def ai_status():
    """Check AI availability and configuration."""
    return {
        "enabled": settings.ai_enabled,
        "available": settings.ai_available,
        "model": settings.anthropic_model if settings.anthropic_api_key else settings.openai_model,
        "provider": "anthropic" if settings.anthropic_api_key else ("openai" if settings.openai_api_key else "none"),
        "timeout_seconds": settings.ai_timeout_seconds,
        "cache_ttl_seconds": settings.ai_cache_ttl_seconds,
    }


@router.post("/filter-signal", response_model=TradeFilterResponse)
async def filter_trade_signal(
    req: TradeFilterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Evaluate a trade signal with AI filtering."""
    market = (await db.execute(
        select(Market).where(Market.condition_id == req.condition_id)
    )).scalar_one_or_none()

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    signal_data = {
        "strategy": req.strategy,
        "side": req.side,
        "outcome": req.outcome,
        "target_price": req.target_price,
        "suggested_size_usdc": req.suggested_size_usdc,
        "strategy_win_rate": 0.5,  # TODO: pull from strategy stats
        "strategy_trade_count": 0,
    }

    market_context = {
        "question": market.question,
        "best_bid": market.best_bid,
        "best_ask": market.best_ask,
        "spread_pct": market.spread_pct,
        "volume_24h": market.volume_24h,
        "liquidity": market.liquidity,
        "ai_score": market.ai_score,
    }

    result = await filter_signal(signal_data, market_context)

    return TradeFilterResponse(
        confidence=result.get("confidence", 0.5),
        decision=result.get("decision", "skip"),
        size_modifier=result.get("size_modifier", 1.0),
        reasoning=result.get("reasoning", ""),
        key_concern=result.get("key_concern"),
        urgency=result.get("urgency", "medium"),
        is_fallback=result.get("_fallback", False),
    )


@router.get("/optimize", response_model=OptimizationResponse)
async def get_optimizations(db: AsyncSession = Depends(get_db)):
    """Get AI parameter optimization suggestions."""
    from src.services.risk_engine import get_risk_params

    params = get_risk_params()
    current_params = {
        "slippage_limit_pct": params.max_slippage_pct,
        "max_position_size_usdc": params.max_position_size_usdc,
        "max_spread_pct": params.max_spread_pct,
    }

    performance_data = {
        "recent_trades": [],  # TODO: pull from DB
        "win_rate_by_strategy": {},
        "avg_slippage_pct": 0.02,
        "pnl_trend": [],
        "market_regime": "unknown",
    }

    result = await suggest_optimizations(performance_data, current_params)

    return OptimizationResponse(
        suggestions=result.get("suggestions", []),
        overall_assessment=result.get("overall_assessment", ""),
        priority=result.get("priority", "low"),
        status=result.get("status", "pending_review"),
        generated_at=result.get("generated_at"),
    )


@router.get("/logs")
async def get_ai_logs(
    limit: int = Query(50, ge=1, le=200),
    component: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve AI decision logs for transparency."""
    query = select(AILog)
    if component:
        query = query.where(AILog.component == component)

    query = query.order_by(desc(AILog.created_at)).limit(limit)
    logs = list((await db.execute(query)).scalars().all())

    return [
        {
            "id": l.id,
            "component": l.component,
            "model": l.model,
            "latency_ms": l.latency_ms,
            "cache_hit": l.cache_hit,
            "success": l.success,
            "output_parsed": l.output_parsed,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/anomalies/{condition_id}")
async def check_market_anomalies(
    condition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run anomaly detection on a specific market."""
    market = (await db.execute(
        select(Market).where(Market.condition_id == condition_id)
    )).scalar_one_or_none()

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    anomalies = detect_market_anomalies(
        condition_id=condition_id,
        current_data={
            "spread_pct": market.spread_pct or 0,
            "liquidity": market.liquidity,
        },
        historical_data={},
    )

    return {"condition_id": condition_id, "anomalies": anomalies}
