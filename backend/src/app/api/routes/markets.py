from fastapi import APIRouter, Depends, Query

from app.services.market_discovery import MarketDiscoveryService, get_market_discovery_service

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/discover")
async def discover_markets(
    ai_enabled: bool = Query(True, description="Enable AI-assisted scoring for passed markets."),
    limit: int = Query(10, ge=1, le=50),
    service: MarketDiscoveryService = Depends(get_market_discovery_service),
) -> dict:
    response = await service.discover_markets(ai_enabled=ai_enabled, limit=limit)
    return response.model_dump()
