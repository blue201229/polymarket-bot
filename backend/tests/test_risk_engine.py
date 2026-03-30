"""Tests for the risk engine — the most critical non-AI component."""
import pytest
from src.services.risk_engine import RiskEngine, RiskParams


def make_engine(**overrides) -> RiskEngine:
    defaults = dict(
        max_position_size_usdc=100,
        max_total_exposure_usdc=1000,
        max_positions=5,
        min_liquidity=5000,
        max_spread_pct=0.08,
        max_slippage_pct=0.02,
        paper_trading=True,
    )
    defaults.update(overrides)
    return RiskEngine(RiskParams(**defaults))


def check(engine, **overrides):
    defaults = dict(
        trade_size_usdc=20,
        market_liquidity=50000,
        market_spread_pct=0.02,
        target_price=0.5,
        current_positions_count=0,
        current_total_exposure_usdc=0,
        is_paper=True,
    )
    defaults.update(overrides)
    return engine.check(**defaults)


def test_valid_trade_approved():
    engine = make_engine()
    result = check(engine)
    assert result.approved is True


def test_oversized_trade_rejected():
    engine = make_engine(max_position_size_usdc=100)
    result = check(engine, trade_size_usdc=150)
    assert result.approved is False
    assert "position_size_exceeded" in result.rejection_reason


def test_total_exposure_exceeded():
    engine = make_engine(max_total_exposure_usdc=1000)
    result = check(engine, trade_size_usdc=50, current_total_exposure_usdc=980)
    assert result.approved is False
    assert "total_exposure_exceeded" in result.rejection_reason


def test_max_positions_reached():
    engine = make_engine(max_positions=5)
    result = check(engine, current_positions_count=5)
    assert result.approved is False
    assert "max_positions_reached" in result.rejection_reason


def test_insufficient_liquidity():
    engine = make_engine(min_liquidity=5000)
    result = check(engine, market_liquidity=500)
    assert result.approved is False
    assert "insufficient_liquidity" in result.rejection_reason


def test_spread_too_wide():
    engine = make_engine(max_spread_pct=0.08)
    result = check(engine, market_spread_pct=0.15)
    assert result.approved is False
    assert "spread_too_wide" in result.rejection_reason


def test_trading_paused():
    engine = make_engine()
    engine.pause_trading("test")
    result = check(engine)
    assert result.approved is False
    assert "trading_paused" in result.rejection_reason


def test_resume_trading():
    engine = make_engine()
    engine.pause_trading("test")
    engine.resume_trading()
    result = check(engine)
    assert result.approved is True


def test_live_order_blocked_in_paper_mode():
    engine = make_engine(paper_trading=True)
    result = check(engine, is_paper=False)
    assert result.approved is False
    assert "paper_trading_mode_active" in result.rejection_reason


def test_zero_size_rejected():
    engine = make_engine()
    result = check(engine, trade_size_usdc=0)
    assert result.approved is False


def test_ai_confidence_warning_only():
    """AI confidence should generate warning, never reject."""
    engine = make_engine()
    result = check(engine, ai_confidence=0.1)
    assert result.approved is True
    assert any("low_ai_confidence" in w for w in result.warnings)
