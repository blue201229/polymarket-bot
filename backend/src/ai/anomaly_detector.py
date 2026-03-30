from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.anomaly_detector")

ANOMALY_SYSTEM = """You are a real-time market anomaly detection system for prediction markets.
Analyze the provided market data snapshot and identify any anomalies that could indicate
risk or opportunity. Be precise and avoid false positives. Return only valid JSON."""

ANOMALY_PROMPT = """Analyze this market data snapshot for anomalies.

Market: {question}
Current Prices: {prices}
Price 1h Ago: {prices_1h}
Price 24h Ago: {prices_24h}

Orderbook:
- Best Bid: {best_bid} (size: ${bid_size:,.0f})
- Best Ask: {best_ask} (size: ${ask_size:,.0f})
- Spread: {spread_bps} bps
- Spread 1h Ago: {spread_1h_bps} bps

Volume:
- 24h Volume: ${volume_24h:,.0f}
- Avg 7d Daily Volume: ${avg_daily_volume:,.0f}
- Volume Change: {volume_change_pct}%

Liquidity:
- Current: ${liquidity:,.0f}
- 1h Ago: ${liquidity_1h:,.0f}
- Change: {liquidity_change_pct}%

Recent Large Trades:
{large_trades}

Return ONLY a JSON object:
{{
  "anomalies": [
    {{
      "type": "<spread_anomaly|volume_spike|liquidity_drop|price_jump|whale_activity|manipulation_risk>",
      "severity": "<low|medium|high|critical>",
      "description": "<what was detected>",
      "suggested_action": "<monitor|tighten_risk|pause_trading|alert>"
    }}
  ],
  "overall_risk_level": "<normal|elevated|high|critical>",
  "market_health_score": <float 0-10>,
  "reasoning": "<brief summary>"
}}"""


@dataclass
class Anomaly:
    anomaly_type: str
    severity: str
    description: str
    suggested_action: str


@dataclass
class AnomalyReport:
    anomalies: list[Anomaly] = field(default_factory=list)
    overall_risk_level: str = "normal"
    market_health_score: float = 10.0
    reasoning: str = ""
    cached: bool = False
    latency_ms: int = 0

    @property
    def has_critical(self) -> bool:
        return any(a.severity == "critical" for a in self.anomalies)

    @property
    def has_high(self) -> bool:
        return any(a.severity in ("high", "critical") for a in self.anomalies)

    @property
    def should_pause(self) -> bool:
        return any(a.suggested_action == "pause_trading" for a in self.anomalies)


class AnomalyDetector:
    """
    AI-assisted anomaly / risk detection.

    Monitors market data for unusual behavior patterns:
    - Abnormal spread widening
    - Sudden liquidity drops
    - Volume spikes
    - Suspicious whale activity
    - Potential manipulation

    Triggers warnings and risk-tightening suggestions.
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine

    async def detect(self, market_snapshot: dict[str, Any]) -> AnomalyReport:
        large_trades_str = "\n".join(
            f"  - {t.get('side', '?')} ${t.get('size', 0):,.0f} @ {t.get('price', 0):.3f} "
            f"({t.get('timestamp', '?')})"
            for t in market_snapshot.get("large_trades", [])[-10:]
        )

        prompt = ANOMALY_PROMPT.format(
            question=market_snapshot.get("question", ""),
            prices=market_snapshot.get("prices", "N/A"),
            prices_1h=market_snapshot.get("prices_1h", "N/A"),
            prices_24h=market_snapshot.get("prices_24h", "N/A"),
            best_bid=market_snapshot.get("best_bid", 0),
            bid_size=market_snapshot.get("bid_size", 0),
            best_ask=market_snapshot.get("best_ask", 0),
            ask_size=market_snapshot.get("ask_size", 0),
            spread_bps=market_snapshot.get("spread_bps", 0),
            spread_1h_bps=market_snapshot.get("spread_1h_bps", 0),
            volume_24h=market_snapshot.get("volume_24h", 0),
            avg_daily_volume=market_snapshot.get("avg_daily_volume", 0),
            volume_change_pct=market_snapshot.get("volume_change_pct", 0),
            liquidity=market_snapshot.get("liquidity", 0),
            liquidity_1h=market_snapshot.get("liquidity_1h", 0),
            liquidity_change_pct=market_snapshot.get("liquidity_change_pct", 0),
            large_trades=large_trades_str or "  None detected",
        )

        response = await self._engine.complete(
            prompt=prompt,
            system=ANOMALY_SYSTEM,
            temperature=0.1,
            max_tokens=512,
        )

        if response is None:
            logger.warning("AI anomaly detection unavailable")
            return AnomalyReport(reasoning="AI unavailable")

        try:
            data = response.parse_json()
            anomalies = [
                Anomaly(
                    anomaly_type=a.get("type", "unknown"),
                    severity=a.get("severity", "low"),
                    description=a.get("description", ""),
                    suggested_action=a.get("suggested_action", "monitor"),
                )
                for a in data.get("anomalies", [])
            ]
            return AnomalyReport(
                anomalies=anomalies,
                overall_risk_level=data.get("overall_risk_level", "normal"),
                market_health_score=float(data.get("market_health_score", 10)),
                reasoning=data.get("reasoning", ""),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse anomaly report", error=str(e))
            return AnomalyReport(reasoning=f"Parse error: {e}")
