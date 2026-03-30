import pytest

from backend.src.services.market_discovery import MarketFilters


def test_filters_pass_valid_market():
    filters = MarketFilters(min_volume=1000, min_liquidity=500, min_volume_24h=100)
    ok, reason = filters.passes({
        "volume": 5000,
        "liquidity": 2000,
        "volume_24h": 500,
        "closed": False,
    })
    assert ok is True
    assert reason == "passed"


def test_filters_reject_low_volume():
    filters = MarketFilters(min_volume=1000)
    ok, reason = filters.passes({"volume": 100, "liquidity": 2000, "closed": False})
    assert ok is False
    assert "volume" in reason


def test_filters_reject_low_liquidity():
    filters = MarketFilters(min_liquidity=500)
    ok, reason = filters.passes({"volume": 5000, "liquidity": 100, "closed": False})
    assert ok is False
    assert "liquidity" in reason


def test_filters_reject_closed_market():
    filters = MarketFilters(exclude_resolved=True)
    ok, reason = filters.passes({"volume": 5000, "liquidity": 2000, "closed": True})
    assert ok is False
    assert "closed" in reason


def test_filters_allow_closed_when_not_excluded():
    filters = MarketFilters(exclude_resolved=False)
    ok, reason = filters.passes({"volume": 5000, "liquidity": 2000, "closed": True})
    assert ok is True
