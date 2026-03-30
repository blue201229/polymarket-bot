import pytest

from backend.src.services.strategies.value import ValueStrategy
from backend.src.services.strategies.momentum import MomentumStrategy
from backend.src.services.strategies.arbitrage import ArbitrageStrategy


@pytest.fixture
def value_strategy():
    return ValueStrategy(min_edge=0.05, base_size=10.0)


@pytest.fixture
def momentum_strategy():
    return MomentumStrategy(min_momentum=0.03, base_size=8.0)


@pytest.fixture
def arb_strategy():
    return ArbitrageStrategy(min_arb_bps=30, base_size=20.0)


@pytest.mark.asyncio
async def test_value_no_signal_for_empty_outcomes(value_strategy):
    result = await value_strategy.evaluate({"outcomes": []})
    assert result is None


@pytest.mark.asyncio
async def test_value_no_signal_for_high_price(value_strategy):
    result = await value_strategy.evaluate({
        "outcomes": [{"price": 0.95, "token_id": "t1", "outcome": "Yes"}],
        "volume_24h": 10000,
    })
    assert result is None


@pytest.mark.asyncio
async def test_value_should_close_take_profit(value_strategy):
    position = {
        "market_id": "m1",
        "condition_id": "c1",
        "token_id": "t1",
        "outcome": "Yes",
        "avg_entry_price": 0.40,
        "current_price": 0.60,
        "size": 10,
    }
    result = await value_strategy.should_close(position, {})
    assert result is not None
    assert result.side == "sell"
    assert "take_profit" in result.reason


@pytest.mark.asyncio
async def test_value_should_close_stop_loss(value_strategy):
    position = {
        "market_id": "m1",
        "condition_id": "c1",
        "token_id": "t1",
        "outcome": "Yes",
        "avg_entry_price": 0.50,
        "current_price": 0.38,
        "size": 10,
    }
    result = await value_strategy.should_close(position, {})
    assert result is not None
    assert result.side == "sell"
    assert "stop_loss" in result.reason


@pytest.mark.asyncio
async def test_momentum_no_signal_without_previous_price(momentum_strategy):
    result = await momentum_strategy.evaluate({
        "outcomes": [{"price": 0.50, "previous_price": 0, "token_id": "t1", "outcome": "Yes"}],
        "volume_24h": 10000,
    })
    assert result is None


@pytest.mark.asyncio
async def test_momentum_no_signal_below_threshold(momentum_strategy):
    result = await momentum_strategy.evaluate({
        "outcomes": [{"price": 0.51, "previous_price": 0.50, "token_id": "t1", "outcome": "Yes"}],
        "volume_24h": 10000,
        "avg_daily_volume": 10000,
    })
    assert result is None


@pytest.mark.asyncio
async def test_arb_detects_underpriced_market(arb_strategy):
    result = await arb_strategy.evaluate({
        "condition_id": "c1",
        "market_id": "m1",
        "question": "Test?",
        "outcomes": [
            {"price": 0.45, "token_id": "t1", "outcome": "Yes"},
            {"price": 0.45, "token_id": "t2", "outcome": "No"},
        ],
        "liquidity": 5000,
    })
    # Sum = 0.90, underpriced by 1000bps
    assert result is not None
    assert result.strategy == "arbitrage"
    assert result.side == "buy"


@pytest.mark.asyncio
async def test_arb_no_signal_for_fair_market(arb_strategy):
    result = await arb_strategy.evaluate({
        "condition_id": "c1",
        "market_id": "m1",
        "question": "Test?",
        "outcomes": [
            {"price": 0.50, "token_id": "t1", "outcome": "Yes"},
            {"price": 0.50, "token_id": "t2", "outcome": "No"},
        ],
        "liquidity": 5000,
    })
    assert result is None


@pytest.mark.asyncio
async def test_arb_no_signal_low_liquidity(arb_strategy):
    result = await arb_strategy.evaluate({
        "condition_id": "c1",
        "market_id": "m1",
        "question": "Test?",
        "outcomes": [
            {"price": 0.40, "token_id": "t1", "outcome": "Yes"},
            {"price": 0.40, "token_id": "t2", "outcome": "No"},
        ],
        "liquidity": 100,
    })
    assert result is None
