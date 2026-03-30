"""
Market discovery API. Discovery is deterministic; AI scoring is optional and separate.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from polymarket_platform.config import Settings, get_settings
from polymarket_platform.models.market import DiscoveredMarket
from polymarket_platform.services.market_discovery import fetch_markets

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/discover", response_model=list[DiscoveredMarket])
async def discover_markets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active: bool | None = Query(True),
    closed: bool | None = Query(False),
    settings: Settings = Depends(get_settings),
) -> list[DiscoveredMarket]:
    """List markets from Gamma (hard filters only)."""
    return await fetch_markets(
        settings,
        limit=limit,
        offset=offset,
        active=active,
        closed=closed,
    )


@router.get("/discover/scored")
async def discover_markets_scored(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active: bool | None = Query(True),
    closed: bool | None = Query(False),
    include_ai: bool = Query(
        False,
        description="When true, attach AI assistant scores (optional; never affects execution).",
    ),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, Any]]:
    """
    Discovery plus optional AI scoring. AI output is advisory and logged; risk engine ignores it.
    """
    markets = await fetch_markets(
        settings,
        limit=limit,
        offset=offset,
        active=active,
        closed=closed,
    )

    if not include_ai:
        return [{"market": m.model_dump(), "ai": None} for m in markets]

    from ai.scoring import score_market

    out: list[dict[str, Any]] = []
    for m in markets:
        md = m.model_dump()
        ai_result = await score_market(md)
        out.append({"market": md, "ai": ai_result})
    return out
