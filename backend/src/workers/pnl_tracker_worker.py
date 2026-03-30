"""
PnL Tracker Worker — tracks position outcomes and updates trade PnL.

Runs periodically to:
1. Find filled trades without PnL
2. Check if markets have resolved
3. Calculate PnL based on resolution outcome
4. Update strategy win/loss records
5. Queue post-trade AI analysis
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, update

from src.core.config import settings
from src.core.database import db_session
from src.core.logging import get_logger
from src.data.polymarket_client import get_polymarket_client
from src.models.trade import Trade, TradeStatus

logger = get_logger(__name__)


class PnLTrackerWorker:

    def __init__(self):
        self._client = get_polymarket_client()
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("pnl_tracker_starting")
        while self._running:
            try:
                await self._track_cycle()
            except Exception as e:
                logger.error("pnl_tracker_error", error=str(e))
            await asyncio.sleep(300)

    async def stop(self) -> None:
        self._running = False

    async def _track_cycle(self) -> None:
        async with db_session() as session:
            result = await session.execute(
                select(Trade)
                .where(
                    Trade.status == TradeStatus.FILLED,
                    Trade.pnl_usdc.is_(None),
                )
                .limit(50)
            )
            pending_trades = result.scalars().all()

        logger.debug("pnl_tracker_cycle", pending=len(pending_trades))

        for trade in pending_trades:
            await self._check_trade_pnl(trade)

    async def _check_trade_pnl(self, trade: Trade) -> None:
        """Check if a trade's market has resolved and calculate PnL."""
        market_data = await self._client.get_market(trade.condition_id)
        if not market_data:
            return

        if not market_data.get("resolved"):
            return  # Market still active

        resolution = market_data.get("resolution", "").upper()
        if not resolution or resolution == "N/A":
            return

        entry_price = trade.executed_price or trade.target_price
        resolution_price = 1.0 if (
            (trade.outcome == "Yes" and resolution == "YES") or
            (trade.outcome == "No" and resolution == "NO")
        ) else 0.0

        if trade.side == "buy":
            pnl_per_share = resolution_price - entry_price
        else:
            pnl_per_share = entry_price - resolution_price

        shares = trade.size_usdc / entry_price if entry_price > 0 else 0
        pnl_usdc = pnl_per_share * shares
        pnl_pct = pnl_per_share / entry_price if entry_price > 0 else 0

        async with db_session() as session:
            await session.execute(
                update(Trade)
                .where(Trade.id == trade.id)
                .values(pnl_usdc=round(pnl_usdc, 4), pnl_pct=round(pnl_pct, 4))
            )

        logger.info(
            "pnl_calculated",
            trade_id=trade.id[:8],
            pnl_usdc=round(pnl_usdc, 4),
            resolution=resolution,
        )

        # Queue post-trade AI analysis (Phase 5)
        if settings.ai_available:
            asyncio.create_task(self._queue_post_trade_analysis(trade.id))

    async def _queue_post_trade_analysis(self, trade_id: str) -> None:
        """Queue AI post-trade analysis — non-blocking."""
        try:
            from src.ai.post_trade import analyze_trade
            from src.core.database import db_session

            async with db_session() as session:
                trade = await session.get(Trade, trade_id)
                if not trade:
                    return

            trade_data = {
                "id": trade.id,
                "source": trade.source,
                "side": trade.side,
                "outcome": trade.outcome,
                "target_price": trade.target_price,
                "executed_price": trade.executed_price,
                "slippage_pct": trade.slippage_pct,
                "size_usdc": trade.size_usdc,
                "pnl_usdc": trade.pnl_usdc,
                "pnl_pct": trade.pnl_pct,
                "ai_confidence": trade.ai_confidence,
                "ai_decision": trade.ai_decision,
                "ai_reasoning": trade.ai_reasoning,
            }

            analysis = await analyze_trade(trade_data, {}, trade_id=trade_id)
            logger.info("post_trade_analysis_complete", trade_id=trade_id[:8], pattern=analysis.get("pattern_tag"))
        except Exception as e:
            logger.error("post_trade_analysis_failed", trade_id=trade_id, error=str(e))
