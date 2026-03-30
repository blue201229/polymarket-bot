from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.ai.trade_filter import TradeEvaluation, TradeFilter
from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger
from backend.src.models.ai_log import AILog
from backend.src.models.position import Position
from backend.src.models.trade import Trade, TradeSide, TradeStatus
from backend.src.services.risk_engine import RiskEngine

logger = get_logger("services.execution")


class ExecutionEngine:
    """
    Core execution engine. Orchestrates the full trade lifecycle:

    Signal -> AI Filter -> Risk Check -> Execute/Paper -> Record

    The pipeline is designed so that:
    - AI provides advisory input (confidence, sizing)
    - Risk engine has absolute veto power
    - Paper trading mode simulates without touching the chain
    - All decisions are logged for auditability
    """

    def __init__(
        self,
        risk_engine: Optional[RiskEngine] = None,
        trade_filter: Optional[TradeFilter] = None,
    ) -> None:
        self._risk = risk_engine or RiskEngine()
        self._trade_filter = trade_filter or TradeFilter()
        self._paper_mode = settings.paper_trading

    async def execute_signal(
        self,
        market_id: str,
        condition_id: str,
        token_id: str,
        outcome: str,
        side: str,
        price: float,
        size: float,
        strategy: str,
        market_context: Optional[dict[str, Any]] = None,
        skip_ai: bool = False,
    ) -> Optional[Trade]:
        """
        Process a trade signal through the full pipeline.

        Returns the Trade object if executed, None if rejected.
        """
        logger.info(
            "Processing signal",
            strategy=strategy,
            side=side,
            outcome=outcome,
            price=price,
            size=size,
        )

        # Step 1: AI trade filter (optional, non-blocking)
        ai_eval: Optional[TradeEvaluation] = None
        if not skip_ai and settings.ai_enabled:
            ai_eval = await self._run_ai_filter(
                strategy=strategy,
                market_context=market_context or {},
                side=side,
                outcome=outcome,
                price=price,
                size=size,
            )

            if ai_eval and ai_eval.recommendation == "skip":
                logger.info(
                    "AI recommends skip",
                    confidence=ai_eval.confidence,
                    reasoning=ai_eval.reasoning[:100],
                )
                trade = await self._record_skipped_trade(
                    market_id=market_id,
                    condition_id=condition_id,
                    token_id=token_id,
                    outcome=outcome,
                    side=side,
                    price=price,
                    size=size,
                    strategy=strategy,
                    ai_eval=ai_eval,
                )
                return trade

        # Step 2: Risk check (DETERMINISTIC - final authority)
        ai_confidence = ai_eval.confidence if ai_eval else None
        ai_size_mod = ai_eval.size_modifier if ai_eval else None
        market_ctx = market_context or {}

        risk_result = await self._risk.check_trade(
            market_id=market_id,
            side=side,
            size=size,
            price=price,
            liquidity=market_ctx.get("liquidity", 0),
            ai_confidence=ai_confidence,
            ai_size_modifier=ai_size_mod,
        )

        if not risk_result.approved:
            logger.warning(
                "Trade rejected by risk engine",
                reason=risk_result.reason,
                strategy=strategy,
            )
            trade = await self._record_rejected_trade(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                strategy=strategy,
                reason=risk_result.reason,
                ai_eval=ai_eval,
            )
            await event_bus.publish(Events.RISK_BREACH, trade=trade, reason=risk_result.reason)
            return trade

        final_size = risk_result.adjusted_size or size

        # Step 3: Execute
        if self._paper_mode:
            trade = await self._paper_execute(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=final_size,
                strategy=strategy,
                ai_eval=ai_eval,
                warnings=risk_result.warnings,
            )
        else:
            trade = await self._live_execute(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=final_size,
                strategy=strategy,
                ai_eval=ai_eval,
                warnings=risk_result.warnings,
            )

        if trade:
            self._risk.record_trade_time(market_id)
            await event_bus.publish(Events.TRADE_EXECUTED, trade=trade)

            await self._update_position(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=final_size,
                strategy=strategy,
            )

        return trade

    async def _run_ai_filter(
        self,
        strategy: str,
        market_context: dict[str, Any],
        side: str,
        outcome: str,
        price: float,
        size: float,
    ) -> Optional[TradeEvaluation]:
        try:
            signal_data = {
                "strategy": strategy,
                "market_question": market_context.get("question", ""),
                "side": side,
                "outcome": outcome,
                "price": price,
                "size": size,
                "best_bid": market_context.get("best_bid", 0),
                "best_ask": market_context.get("best_ask", 0),
                "spread_bps": market_context.get("spread_bps", 0),
                "volume_24h": market_context.get("volume_24h", 0),
                "liquidity": market_context.get("liquidity", 0),
                "time_to_expiry": market_context.get("time_to_expiry", "unknown"),
                "price_history": market_context.get("price_history", []),
                "strategy_win_rate": market_context.get("strategy_win_rate", 50),
                "strategy_avg_pnl": market_context.get("strategy_avg_pnl", 0),
                "strategy_total_trades": market_context.get("strategy_total_trades", 0),
            }
            return await self._trade_filter.evaluate_trade(signal_data)
        except Exception as e:
            logger.error("AI filter error (proceeding without AI)", error=str(e))
            return None

    async def _paper_execute(
        self,
        market_id: str,
        condition_id: str,
        token_id: str,
        outcome: str,
        side: str,
        price: float,
        size: float,
        strategy: str,
        ai_eval: Optional[TradeEvaluation],
        warnings: list[str],
    ) -> Trade:
        async with get_session() as session:
            trade = Trade(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                filled_size=size,
                filled_price=price,
                strategy=strategy,
                status=TradeStatus.PAPER,
                is_paper=True,
                ai_confidence=ai_eval.confidence if ai_eval else None,
                ai_size_modifier=ai_eval.size_modifier if ai_eval else None,
                ai_approved=True,
                notes="; ".join(warnings) if warnings else None,
            )
            session.add(trade)
            logger.info(
                "Paper trade executed",
                side=side,
                outcome=outcome,
                price=price,
                size=size,
                strategy=strategy,
            )
            return trade

    async def _live_execute(
        self,
        market_id: str,
        condition_id: str,
        token_id: str,
        outcome: str,
        side: str,
        price: float,
        size: float,
        strategy: str,
        ai_eval: Optional[TradeEvaluation],
        warnings: list[str],
    ) -> Optional[Trade]:
        """
        Live execution against Polymarket CLOB.
        Requires configured API credentials.
        """
        async with get_session() as session:
            trade = Trade(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                strategy=strategy,
                status=TradeStatus.SUBMITTED,
                is_paper=False,
                ai_confidence=ai_eval.confidence if ai_eval else None,
                ai_size_modifier=ai_eval.size_modifier if ai_eval else None,
                ai_approved=True,
                slippage_bps=settings.default_slippage_bps,
                notes="; ".join(warnings) if warnings else None,
            )
            session.add(trade)

        try:
            order_result = await self._submit_order(
                token_id=token_id,
                side=side,
                price=price,
                size=size,
            )

            async with get_session() as session:
                result = await session.execute(
                    select(Trade).where(Trade.id == trade.id)
                )
                db_trade = result.scalar_one()
                db_trade.order_id = order_result.get("order_id")
                db_trade.status = TradeStatus.FILLED
                db_trade.filled_size = size
                db_trade.filled_price = order_result.get("avg_price", price)
                return db_trade

        except Exception as e:
            logger.error("Live execution failed", error=str(e))
            async with get_session() as session:
                result = await session.execute(
                    select(Trade).where(Trade.id == trade.id)
                )
                db_trade = result.scalar_one()
                db_trade.status = TradeStatus.FAILED
                db_trade.notes = f"Execution failed: {e}"
                return db_trade

    async def _submit_order(
        self, token_id: str, side: str, price: float, size: float
    ) -> dict[str, Any]:
        """Submit order to Polymarket CLOB API."""
        logger.info("Submitting order to CLOB", token_id=token_id[:16], side=side)
        # Placeholder for actual CLOB integration
        # In production, this would use py-clob-client
        return {"order_id": "pending_integration", "avg_price": price}

    async def _record_skipped_trade(
        self, market_id: str, condition_id: str, token_id: str,
        outcome: str, side: str, price: float, size: float,
        strategy: str, ai_eval: TradeEvaluation,
    ) -> Trade:
        async with get_session() as session:
            trade = Trade(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                strategy=strategy,
                status=TradeStatus.CANCELLED,
                is_paper=self._paper_mode,
                ai_confidence=ai_eval.confidence,
                ai_size_modifier=ai_eval.size_modifier,
                ai_approved=False,
                ai_skip_reason=ai_eval.reasoning,
                notes="Skipped by AI filter",
            )
            session.add(trade)
            return trade

    async def _record_rejected_trade(
        self, market_id: str, condition_id: str, token_id: str,
        outcome: str, side: str, price: float, size: float,
        strategy: str, reason: str, ai_eval: Optional[TradeEvaluation],
    ) -> Trade:
        async with get_session() as session:
            trade = Trade(
                market_id=market_id,
                condition_id=condition_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                strategy=strategy,
                status=TradeStatus.CANCELLED,
                is_paper=self._paper_mode,
                ai_confidence=ai_eval.confidence if ai_eval else None,
                ai_approved=False,
                notes=f"Risk rejection: {reason}",
            )
            session.add(trade)
            return trade

    async def _update_position(
        self,
        market_id: str,
        condition_id: str,
        token_id: str,
        outcome: str,
        side: str,
        price: float,
        size: float,
        strategy: str,
    ) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(Position).where(
                    Position.market_id == market_id,
                    Position.token_id == token_id,
                    Position.is_open == True,
                )
            )
            position = result.scalar_one_or_none()

            if side == TradeSide.BUY:
                if position:
                    total_cost = (position.avg_entry_price * position.size) + (price * size)
                    position.size += size
                    position.avg_entry_price = total_cost / position.size if position.size > 0 else 0
                    position.current_price = price
                else:
                    position = Position(
                        market_id=market_id,
                        condition_id=condition_id,
                        token_id=token_id,
                        outcome=outcome,
                        side=side,
                        size=size,
                        avg_entry_price=price,
                        current_price=price,
                        strategy=strategy,
                        is_paper=self._paper_mode,
                    )
                    session.add(position)
            elif side == TradeSide.SELL and position:
                position.size -= size
                pnl = (price - position.avg_entry_price) * size
                position.realized_pnl += pnl
                if position.size <= 0:
                    position.is_open = False
                    position.size = 0
