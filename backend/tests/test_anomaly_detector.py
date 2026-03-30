"""Tests for anomaly detection."""
import pytest
from src.ai.anomaly_detector import (
    detect_market_anomalies,
    should_pause_trading,
    AnomalyType,
    AnomalySeverity,
)

NORMAL_SPREADS = [0.02, 0.021, 0.019, 0.02, 0.022, 0.021, 0.020, 0.019, 0.021, 0.02]


def test_spread_spike_critical():
    anomalies = detect_market_anomalies(
        "test",
        {"spread_pct": 0.15, "liquidity": 50000},
        {"spread_history": NORMAL_SPREADS, "price_history": [], "liquidity_history": []},
    )
    spread_anomalies = [a for a in anomalies if a["type"] == AnomalyType.SPREAD_SPIKE]
    assert len(spread_anomalies) > 0
    assert spread_anomalies[0]["severity"] == AnomalySeverity.CRITICAL


def test_no_anomaly_normal_conditions():
    anomalies = detect_market_anomalies(
        "test",
        {"spread_pct": 0.021, "liquidity": 48000},
        {"spread_history": NORMAL_SPREADS, "price_history": [0.5] * 10, "liquidity_history": [50000] * 5},
    )
    assert len(anomalies) == 0


def test_liquidity_drop_critical():
    anomalies = detect_market_anomalies(
        "test",
        {"spread_pct": 0.02, "liquidity": 5000},
        {"spread_history": [], "price_history": [], "liquidity_history": [100000, 90000, 80000]},
    )
    liq = [a for a in anomalies if a["type"] == AnomalyType.LIQUIDITY_DROP]
    assert len(liq) > 0
    assert liq[0]["severity"] == AnomalySeverity.CRITICAL


def test_should_pause_on_critical():
    critical_anomaly = {
        "type": AnomalyType.SPREAD_SPIKE,
        "severity": AnomalySeverity.CRITICAL,
        "message": "Test",
    }
    should_pause, reason = should_pause_trading([critical_anomaly])
    assert should_pause is True


def test_no_pause_on_warning():
    warning_anomaly = {
        "type": AnomalyType.SPREAD_SPIKE,
        "severity": AnomalySeverity.WARNING,
        "message": "Test",
    }
    should_pause, _ = should_pause_trading([warning_anomaly])
    assert should_pause is False


def test_no_pause_on_empty():
    should_pause, _ = should_pause_trading([])
    assert should_pause is False
