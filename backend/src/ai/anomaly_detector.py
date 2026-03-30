"""
Anomaly Detection — AI detects unusual market and wallet behavior.

Triggers warnings, can suggest risk tightening, never forces pauses.
Operators or configured thresholds control actual system behavior.

Runs continuously on incoming market data and wallet events.
"""
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.logging import get_logger
from src.core.redis_client import Cache, pubsub

logger = get_logger(__name__)

_cache = Cache("ai:anomaly", default_ttl=120)


class AnomalyType:
    SPREAD_SPIKE = "spread_spike"
    LIQUIDITY_DROP = "liquidity_drop"
    PRICE_MANIPULATION = "price_manipulation"
    UNUSUAL_WALLET = "unusual_wallet"
    VOLUME_ANOMALY = "volume_anomaly"
    RAPID_PRICE_MOVE = "rapid_price_move"


class AnomalySeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def _detect_spread_anomaly(
    current_spread: float,
    historical_spreads: List[float],
) -> Optional[Dict[str, Any]]:
    """Deterministic spike detection using z-score."""
    if len(historical_spreads) < 10:
        return None

    mean = statistics.mean(historical_spreads)
    stdev = statistics.stdev(historical_spreads)

    if stdev == 0:
        return None

    z_score = (current_spread - mean) / stdev

    if z_score > 3.0:
        return {
            "type": AnomalyType.SPREAD_SPIKE,
            "severity": AnomalySeverity.CRITICAL,
            "z_score": round(z_score, 2),
            "current": current_spread,
            "historical_mean": round(mean, 4),
            "message": f"Spread {current_spread:.2%} is {z_score:.1f}σ above mean ({mean:.2%})",
            "suggested_action": "pause_trading",
        }
    elif z_score > 2.0:
        return {
            "type": AnomalyType.SPREAD_SPIKE,
            "severity": AnomalySeverity.WARNING,
            "z_score": round(z_score, 2),
            "current": current_spread,
            "historical_mean": round(mean, 4),
            "message": f"Spread elevated: {current_spread:.2%} ({z_score:.1f}σ above mean)",
            "suggested_action": "reduce_size",
        }

    return None


def _detect_liquidity_drop(
    current_liquidity: float,
    historical_liquidity: List[float],
) -> Optional[Dict[str, Any]]:
    """Detect sudden liquidity drops."""
    if not historical_liquidity:
        return None

    peak_liquidity = max(historical_liquidity)
    if peak_liquidity == 0:
        return None

    drop_pct = (peak_liquidity - current_liquidity) / peak_liquidity

    if drop_pct > 0.70:
        return {
            "type": AnomalyType.LIQUIDITY_DROP,
            "severity": AnomalySeverity.CRITICAL,
            "drop_pct": round(drop_pct, 3),
            "current": current_liquidity,
            "peak": peak_liquidity,
            "message": f"Liquidity dropped {drop_pct:.0%} from peak (${peak_liquidity:,.0f} → ${current_liquidity:,.0f})",
            "suggested_action": "halt_entries",
        }
    elif drop_pct > 0.40:
        return {
            "type": AnomalyType.LIQUIDITY_DROP,
            "severity": AnomalySeverity.WARNING,
            "drop_pct": round(drop_pct, 3),
            "current": current_liquidity,
            "peak": peak_liquidity,
            "message": f"Liquidity dropped {drop_pct:.0%} from peak",
            "suggested_action": "reduce_size",
        }

    return None


def _detect_price_move_anomaly(
    price_history: List[float],
    window: int = 10,
) -> Optional[Dict[str, Any]]:
    """Detect rapid price moves using rolling returns."""
    if len(price_history) < window + 1:
        return None

    recent = price_history[-window:]
    start_price = recent[0]
    end_price = recent[-1]

    if start_price == 0:
        return None

    move = abs(end_price - start_price) / start_price

    if move > 0.15:
        return {
            "type": AnomalyType.RAPID_PRICE_MOVE,
            "severity": AnomalySeverity.WARNING,
            "move_pct": round(move, 3),
            "from_price": start_price,
            "to_price": end_price,
            "window_ticks": window,
            "message": f"Price moved {move:.1%} over last {window} ticks",
            "suggested_action": "wait_for_stabilization",
        }

    return None


def detect_market_anomalies(
    condition_id: str,
    current_data: Dict[str, Any],
    historical_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Run all deterministic anomaly detectors on a market.

    Returns list of detected anomalies (may be empty).
    This is synchronous and fast — no AI call needed for real-time detection.
    AI is used for deeper analysis of confirmed anomalies (Phase 4).
    """
    anomalies = []

    spread_anomaly = _detect_spread_anomaly(
        current_data.get("spread_pct", 0),
        historical_data.get("spread_history", []),
    )
    if spread_anomaly:
        spread_anomaly["condition_id"] = condition_id
        anomalies.append(spread_anomaly)

    liquidity_anomaly = _detect_liquidity_drop(
        current_data.get("liquidity", 0),
        historical_data.get("liquidity_history", []),
    )
    if liquidity_anomaly:
        liquidity_anomaly["condition_id"] = condition_id
        anomalies.append(liquidity_anomaly)

    price_anomaly = _detect_price_move_anomaly(
        historical_data.get("price_history", []),
    )
    if price_anomaly:
        price_anomaly["condition_id"] = condition_id
        anomalies.append(price_anomaly)

    return anomalies


async def publish_anomalies(anomalies: List[Dict[str, Any]]) -> None:
    """Publish detected anomalies to all connected frontends via pub/sub."""
    for anomaly in anomalies:
        anomaly["detected_at"] = datetime.now(timezone.utc).isoformat()
        await pubsub.publish("anomaly", anomaly)
        logger.warning(
            "anomaly_detected",
            type=anomaly["type"],
            severity=anomaly["severity"],
            message=anomaly.get("message"),
        )


def should_pause_trading(anomalies: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Deterministic check: should the system halt new entries due to anomalies?
    This is a hard rule — AI cannot override it.
    """
    critical = [a for a in anomalies if a.get("severity") == AnomalySeverity.CRITICAL]
    if critical:
        return True, critical[0].get("message", "Critical anomaly detected")
    return False, ""
