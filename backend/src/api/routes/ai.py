from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db
from backend.src.models.ai_log import AILog

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/logs")
async def list_ai_logs(
    limit: int = Query(default=50, le=200),
    module: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(AILog).order_by(AILog.created_at.desc())
    if module:
        query = query.where(AILog.module == module)
    query = query.limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": l.id,
                "module": l.module,
                "action": l.action,
                "provider": l.provider,
                "model": l.model,
                "latency_ms": l.latency_ms,
                "tokens_used": l.tokens_used,
                "success": l.success,
                "error": l.error,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "created_at": str(l.created_at),
            }
            for l in logs
        ],
        "total": len(logs),
    }


@router.get("/impact")
async def ai_impact_report(days: int = Query(default=30, le=90)) -> dict:
    from backend.src.services.performance import PerformanceService

    service = PerformanceService()
    return await service.get_ai_impact_report(days=days)


@router.post("/optimize")
async def run_optimization(days: int = Query(default=7, le=30)) -> dict:
    from backend.src.services.performance import PerformanceService

    service = PerformanceService()
    result = await service.run_optimization(days=days)
    return {
        "suggestions": [
            {
                "parameter": s.parameter,
                "current_value": s.current_value,
                "suggested_value": s.suggested_value,
                "change_percent": s.change_percent,
                "reasoning": s.reasoning,
            }
            for s in result.suggestions
        ],
        "overall_assessment": result.overall_assessment,
        "confidence": result.confidence,
        "risk_level": result.risk_level,
    }


@router.post("/analyze")
async def run_post_trade_analysis(days: int = Query(default=7, le=30)) -> dict:
    from backend.src.services.performance import PerformanceService

    service = PerformanceService()
    report = await service.run_post_trade_analysis(days=days)
    return {
        "insights": [
            {
                "category": i.category,
                "finding": i.finding,
                "impact": i.impact,
                "suggestion": i.suggestion,
            }
            for i in report.insights
        ],
        "top_improvement": report.top_improvement,
        "strategy_grades": report.strategy_grades,
        "overall_assessment": report.overall_assessment,
    }
