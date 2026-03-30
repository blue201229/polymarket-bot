from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary")
async def performance_summary(days: int = Query(default=7, le=90)) -> dict:
    from backend.src.services.performance import PerformanceService

    service = PerformanceService()
    summary = await service.get_summary(days=days)

    # Remove raw trade list from summary response
    summary.pop("trades", None)
    return summary


@router.get("/strategies")
async def strategy_performance(days: int = Query(default=7, le=90)) -> dict:
    from backend.src.services.performance import PerformanceService

    service = PerformanceService()
    summary = await service.get_summary(days=days)
    return {
        "window_days": days,
        "strategies": summary.get("strategies", {}),
    }
