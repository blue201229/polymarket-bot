from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db
from backend.src.models.alert import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    limit: int = Query(default=50, le=200),
    severity: Optional[str] = None,
    unacknowledged_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Alert).order_by(Alert.created_at.desc())

    if severity:
        query = query.where(Alert.severity == severity)
    if unacknowledged_only:
        query = query.where(Alert.acknowledged == False)

    query = query.limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "source": a.source,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "acknowledged": a.acknowledged,
                "created_at": str(a.created_at),
            }
            for a in alerts
        ],
        "total": len(alerts),
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(
        update(Alert).where(Alert.id == alert_id).values(acknowledged=True)
    )
    return {"message": "Alert acknowledged"}
