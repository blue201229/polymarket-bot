from fastapi import APIRouter, Query

from core.models import MarketDiscoveryResponse
from services.market_discovery import apply_hard_filters, discover_markets

router = APIRouter()


@router.get("", response_model=MarketDiscoveryResponse)
async def list_markets(
    min_volume_24h: float = Query(default=1000.0, ge=0),
    max_spread_bps: int = Query(default=120, ge=1),
) -> MarketDiscoveryResponse:
    markets = discover_markets()
    filtered = apply_hard_filters(markets, min_volume=min_volume_24h, max_spread_bps=max_spread_bps)
    return MarketDiscoveryResponse(hard_filter_count=len(filtered), markets=filtered)
