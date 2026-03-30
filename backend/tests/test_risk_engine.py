import pytest
from unittest.mock import AsyncMock, patch

from backend.src.services.risk_engine import RiskEngine, RiskLimits


@pytest.fixture
def risk_engine():
    limits = RiskLimits(
        max_position_size_usd=100.0,
        max_daily_loss_usd=50.0,
        max_open_positions=5,
        max_single_trade_usd=50.0,
        min_liquidity_usd=500.0,
        max_slippage_bps=200,
        cooldown_seconds=0,
    )
    return RiskEngine(limits=limits)


@pytest.mark.asyncio
async def test_approve_valid_trade(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=5000.0,
        )
        assert result.approved is True


@pytest.mark.asyncio
async def test_reject_trade_exceeding_single_limit(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=200.0,
            price=0.50,
            liquidity=5000.0,
        )
        assert result.approved is False
        assert "single trade limit" in result.reason.lower()


@pytest.mark.asyncio
async def test_reject_trade_max_positions(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=5), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=5000.0,
        )
        assert result.approved is False
        assert "max open positions" in result.reason.lower()


@pytest.mark.asyncio
async def test_reject_insufficient_liquidity(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=100.0,
        )
        assert result.approved is False
        assert "liquidity" in result.reason.lower()


@pytest.mark.asyncio
async def test_ai_size_modifier_clamped(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=5000.0,
            ai_size_modifier=2.0,  # should be clamped to 1.2
        )
        assert result.approved is True
        assert any("clamped" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_risk_tightening(risk_engine):
    risk_engine.tighten_risk(0.5)

    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=5000.0,
        )
        assert result.approved is True
        assert result.adjusted_size is not None
        assert result.adjusted_size < 10.0
        assert any("tightened" in w.lower() for w in result.warnings)

    risk_engine.reset_risk()


@pytest.mark.asyncio
async def test_low_ai_confidence_warning(risk_engine):
    with patch.object(risk_engine, '_get_daily_loss', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_count_open_positions', new_callable=AsyncMock, return_value=0), \
         patch.object(risk_engine, '_get_position_size', new_callable=AsyncMock, return_value=0):
        result = await risk_engine.check_trade(
            market_id="test_market",
            side="buy",
            size=10.0,
            price=0.50,
            liquidity=5000.0,
            ai_confidence=0.1,
        )
        assert result.approved is True  # Low confidence warns but doesn't block
        assert any("low ai confidence" in w.lower() for w in result.warnings)
