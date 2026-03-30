from __future__ import annotations

import asyncio
from typing import Any, Optional

from backend.src.ai.anomaly_detector import AnomalyDetector, AnomalyReport
from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger
from backend.src.models.alert import Alert, AlertSeverity

logger = get_logger("services.anomaly_monitor")


class AnomalyMonitor:
    """
    Continuous anomaly monitoring service.

    Runs periodically to check active markets for anomalies using
    AI-assisted detection. When anomalies are found:
    - Creates alerts
    - Optionally tightens risk parameters
    - Notifies via Telegram/Discord

    The anomaly detector is AI-powered but the response actions
    are deterministic (alert, tighten risk, suggest pause).
    """

    def __init__(
        self,
        detector: Optional[AnomalyDetector] = None,
        check_interval: int = 60,
    ) -> None:
        self._detector = detector or AnomalyDetector()
        self._check_interval = check_interval
        self._running = False
        self._risk_engine = None

    def set_risk_engine(self, risk_engine: Any) -> None:
        self._risk_engine = risk_engine

    async def start(self) -> None:
        self._running = True
        logger.info("Anomaly monitor started", interval=self._check_interval)
        while self._running:
            try:
                await self._check_all_markets()
            except Exception as e:
                logger.error("Anomaly check error", error=str(e))
            await asyncio.sleep(self._check_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("Anomaly monitor stopped")

    async def check_market(self, market_snapshot: dict[str, Any]) -> AnomalyReport:
        report = await self._detector.detect(market_snapshot)

        if report.anomalies:
            await self._handle_anomalies(report, market_snapshot)

        return report

    async def _check_all_markets(self) -> None:
        """Check active markets with open positions for anomalies."""
        from backend.src.models.position import Position
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(Position.condition_id).where(Position.is_open == True).distinct()
            )
            active_conditions = [r[0] for r in result.all()]

        if not active_conditions:
            return

        for condition_id in active_conditions:
            snapshot = await self._build_market_snapshot(condition_id)
            if snapshot:
                await self.check_market(snapshot)

    async def _build_market_snapshot(self, condition_id: str) -> Optional[dict[str, Any]]:
        """Build market snapshot for anomaly detection."""
        from backend.src.models.market import Market
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(Market).where(Market.condition_id == condition_id)
            )
            market = result.scalar_one_or_none()
            if not market:
                return None

            return {
                "question": market.question,
                "condition_id": condition_id,
                "prices": f"current: spread={market.spread}",
                "prices_1h": "N/A",
                "prices_24h": "N/A",
                "best_bid": 0,
                "bid_size": 0,
                "best_ask": 0,
                "ask_size": 0,
                "spread_bps": int((market.spread or 0) * 10000),
                "spread_1h_bps": 0,
                "volume_24h": market.volume_24h,
                "avg_daily_volume": market.volume / 30 if market.volume else 0,
                "volume_change_pct": 0,
                "liquidity": market.liquidity,
                "liquidity_1h": market.liquidity,
                "liquidity_change_pct": 0,
                "large_trades": [],
            }

    async def _handle_anomalies(
        self, report: AnomalyReport, snapshot: dict[str, Any]
    ) -> None:
        for anomaly in report.anomalies:
            severity_map = {
                "low": AlertSeverity.INFO,
                "medium": AlertSeverity.WARNING,
                "high": AlertSeverity.CRITICAL,
                "critical": AlertSeverity.CRITICAL,
            }
            severity = severity_map.get(anomaly.severity, AlertSeverity.INFO)

            async with get_session() as session:
                alert = Alert(
                    alert_type=f"anomaly_{anomaly.anomaly_type}",
                    severity=severity,
                    title=f"Anomaly: {anomaly.anomaly_type}",
                    message=anomaly.description,
                    source="anomaly_detector",
                    entity_type="market",
                    entity_id=snapshot.get("condition_id", ""),
                )
                session.add(alert)

            await event_bus.publish(
                Events.ANOMALY_DETECTED,
                anomaly=anomaly,
                report=report,
                snapshot=snapshot,
            )

        if report.has_critical and self._risk_engine:
            self._risk_engine.tighten_risk(0.5)
            logger.warning("Risk tightened due to critical anomaly")
        elif report.has_high and self._risk_engine:
            self._risk_engine.tighten_risk(0.75)
            logger.warning("Risk tightened due to high-severity anomaly")

        if report.should_pause:
            await event_bus.publish(
                Events.ALERT_CREATED,
                title="Trading Pause Suggested",
                message=f"Anomaly detector recommends pausing: {report.reasoning}",
                severity="critical",
            )
