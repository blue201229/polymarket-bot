from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from core.models import Market


def _seed_markets() -> list[Market]:
    now = datetime.now(timezone.utc)
    return [
        Market(
            market_id="mkt_us_election_2028",
            question="Will candidate X win the 2028 US election?",
            category="politics",
            volume_24h=315_000,
            liquidity=185_000,
            spread_bps=52,
            yes_price=0.44,
            no_price=0.56,
            volatility_24h=0.09,
            resolves_at=now + timedelta(days=600),
        ),
        Market(
            market_id="mkt_eth_5k_2026",
            question="Will ETH exceed $5,000 by Dec 31, 2026?",
            category="crypto",
            volume_24h=890_000,
            liquidity=510_000,
            spread_bps=34,
            yes_price=0.37,
            no_price=0.63,
            volatility_24h=0.14,
            resolves_at=now + timedelta(days=260),
        ),
        Market(
            market_id="mkt_movie_award",
            question="Will Movie A win best picture this year?",
            category="entertainment",
            volume_24h=22_000,
            liquidity=11_000,
            spread_bps=190,
            yes_price=0.22,
            no_price=0.78,
            volatility_24h=0.04,
            resolves_at=now + timedelta(days=120),
        ),
    ]


def discover_markets() -> list[Market]:
    # Phase 1: seeded data source; in Phase 2 this becomes live ingestion.
    return _seed_markets()


def apply_hard_filters(markets: Iterable[Market], min_volume: float, max_spread_bps: int) -> list[Market]:
    return [
        m
        for m in markets
        if m.volume_24h >= min_volume and m.spread_bps <= max_spread_bps
    ]
