"""Tests for trading strategies."""
import asyncio
import pytest
from src.services.strategies.base import StrategyConfig
from src.services.strategies.momentum import MomentumStrategy
from src.services.strategies.arbitrage import ArbitrageStrategy


def make_market(condition_id="test-123", **overrides):
    defaults = {
        "condition_id": condition_id,
        "question": "Test market",
        "liquidity": 50000,
        "spread_pct": 0.02,
        "ai_score": 7.0,
        "price_history": [0.50, 0.51, 0.52, 0.53, 0.54],
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.asyncio
async def test_momentum_strong_signal():
    strategy = MomentumStrategy(StrategyConfig(name="test", base_size_usdc=20, entry_threshold=0.03))
    market = make_market(price_history=[0.40, 0.43, 0.46, 0.49, 0.52])
    signal = await strategy.analyze(market)
    assert signal is not None
    assert signal.side == "buy"
    assert signal.outcome == "Yes"


@pytest.mark.asyncio
async def test_momentum_no_signal_flat():
    strategy = MomentumStrategy(StrategyConfig(name="test", base_size_usdc=20, entry_threshold=0.05))
    market = make_market(price_history=[0.50, 0.50, 0.51, 0.50, 0.50])
    signal = await strategy.analyze(market)
    assert signal is None


@pytest.mark.asyncio
async def test_momentum_no_signal_low_liquidity():
    strategy = MomentumStrategy(StrategyConfig(name="test", base_size_usdc=20, min_liquidity=10000))
    market = make_market(liquidity=500, price_history=[0.40, 0.43, 0.46, 0.49, 0.52])
    signal = await strategy.analyze(market)
    assert signal is None


@pytest.mark.asyncio
async def test_momentum_cooldown():
    strategy = MomentumStrategy(StrategyConfig(name="test", base_size_usdc=20, cooldown_seconds=3600))
    market = make_market(price_history=[0.40, 0.43, 0.46, 0.49, 0.52])
    strategy.set_cooldown(market["condition_id"])
    signal = await strategy.analyze(market)
    assert signal is None


@pytest.mark.asyncio
async def test_momentum_avoids_extreme_prices():
    strategy = MomentumStrategy(StrategyConfig(name="test", base_size_usdc=20, entry_threshold=0.01))
    market = make_market(price_history=[0.91, 0.92, 0.93, 0.94, 0.95])  # Already > 0.92
    signal = await strategy.analyze(market)
    assert signal is None  # Should avoid because > 0.92


@pytest.mark.asyncio
async def test_arbitrage_detects_opportunity():
    strategy = ArbitrageStrategy(StrategyConfig(name="arb", base_size_usdc=30))
    market = make_market(yes_ask=0.45, no_ask=0.45)  # Sum = 0.90
    signal = await strategy.analyze(market)
    assert signal is not None
    assert signal.strategy == "arbitrage"


@pytest.mark.asyncio
async def test_arbitrage_no_signal_fair_pricing():
    strategy = ArbitrageStrategy(StrategyConfig(name="arb", base_size_usdc=30))
    market = make_market(yes_ask=0.51, no_ask=0.50)  # Sum = 1.01 — no arb profit
    signal = await strategy.analyze(market)
    assert signal is None


@pytest.mark.asyncio
async def test_arbitrage_missing_no_ask():
    strategy = ArbitrageStrategy(StrategyConfig(name="arb", base_size_usdc=30))
    market = make_market(yes_ask=0.45)  # No no_ask
    signal = await strategy.analyze(market)
    assert signal is None
