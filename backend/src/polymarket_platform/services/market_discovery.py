"""
Market discovery via Polymarket Gamma API (read-only, deterministic).
AI does not run here; scoring is applied in the AI layer when requested.
"""

from datetime import datetime
from typing import Any

import httpx

from polymarket_platform.config import Settings
from polymarket_platform.models.market import DiscoveredMarket


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_market(item: dict[str, Any]) -> DiscoveredMarket:
    mid = str(item.get("id") or item.get("conditionId") or "")
    return DiscoveredMarket(
        id=mid,
        slug=item.get("slug"),
        question=str(item.get("question") or item.get("title") or ""),
        condition_id=item.get("conditionId") or item.get("condition_id"),
        active=bool(item.get("active", True)),
        closed=bool(item.get("closed", False)),
        end_date=_parse_dt(item.get("endDate") or item.get("end_date")),
        volume=_to_float(item.get("volume")),
        liquidity=_to_float(item.get("liquidity")),
        raw=item,
    )


async def fetch_markets(
    settings: Settings,
    *,
    limit: int = 50,
    active: bool | None = True,
    closed: bool | None = False,
    offset: int = 0,
) -> list[DiscoveredMarket]:
    """
    List markets from Gamma `/markets` with pagination.
    Hard filters are query params only; no AI.
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if active is not None:
        params["active"] = str(active).lower()
    if closed is not None:
        params["closed"] = str(closed).lower()

    url = f"{settings.polymarket_gamma_base_url.rstrip('/')}/markets"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list):
        return []

    return [_normalize_market(item) for item in data if isinstance(item, dict)]
