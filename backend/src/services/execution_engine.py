"""
Execution Engine — the final step in the trade pipeline.

Pipeline:
  Strategy Signal → AI Filter (advisory) → Risk Engine (hard) → Execution Engine

The execution engine:
1. Validates risk one final time (defensive)
2. Routes to paper trading or live execution
3. Records the trade
4. Publishes result to frontends
5. Queues post-trade analysis

Paper trading mode is the default — enabled via PAPER_TRADING_MODE=true.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import db_session
from src.core.exceptions import ExecutionError, RiskEngineError
from src.core.logging import get_logger
from src.core.redis_client import pubsub
from src.data.polymarket_client import get_polymarket_client
from src.models.trade import Trade, TradeStatus, TradeSide, TradeSource
from src.services.risk_engine import get_risk_engine, RiskCheckResult

logger = get_logger(__name__)


class TradeRequest:
    """Input to the execution engine."""

    def __init__(
        self,
        condition_id: str,
        market_id: str,
        side: str,
        outcome: str,
        source: str,
        size_usdc: float,
        target_price: float,
        max_slippage_pct: float = settings.default_slippage_pct,
        # AI advisory fields (always recorded, never override risk)
        ai_confidence: Optional[float] = None,
        ai_size_modifier: Optional[float] = None,
        ai_decision: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        copied_wallet: Optional[str] = None,
    ):
        self.condition_id = condition_id
        self.market_id = market_id
        self.side = side
        self.outcome = outcome
        self.source = source
        self.size_usdc = size_usdc
        self.target_price = target_price
        self.max_slippage_pct = max_slippage_pct
        self.ai_confidence = ai_confidence
        self.ai_size_modifier = ai_size_modifier
        self.ai_decision = ai_decision
        self.ai_reasoning = ai_reasoning
        self.copied_wallet = copied_wallet


class ExecutionEngine:

    def __init__(self):
        self._client = get_polymarket_client()
        self._risk = get_risk_engine()

    async def execute(
        self,
        request: TradeRequest,
        market_liquidity: float,
        market_spread_pct: float,
        current_positions_count: int,
        current_total_exposure_usdc: float,
    ) -> Trade:
        """
        Execute a trade request through the full pipeline.

        Returns the Trade record regardless of outcome (approved/rejected/paper).
        """
        is_paper = settings.paper_trading_mode

        # Final risk check (authoritative — AI cannot bypass this)
        risk_result = self._risk.check(
            trade_size_usdc=request.size_usdc,
            market_liquidity=market_liquidity,
            market_spread_pct=market_spread_pct,
            target_price=request.target_price,
            current_positions_count=current_positions_count,
            current_total_exposure_usdc=current_total_exposure_usdc,
            is_paper=is_paper,
            ai_confidence=request.ai_confidence,
        )

        if not risk_result.approved:
            trade = await self._record_trade(request, risk_result, is_paper)
            logger.info(
                "trade_risk_rejected",
                condition_id=request.condition_id,
                reason=risk_result.rejection_reason,
            )
            return trade

        # Execute
        if is_paper:
            trade = await self._paper_execute(request, risk_result, market_spread_pct)
        else:
            trade = await self._live_execute(request, risk_result)

        # Publish to frontends
        await self._publish_trade_event(trade)

        # Queue post-trade analysis (async, non-blocking)
        if trade.status == TradeStatus.FILLED:
            pass  # Phase 5: asyncio.create_task(analyze_post_trade(trade.id))

        return trade

    async def _paper_execute(
        self,
        request: TradeRequest,
        risk_result: RiskCheckResult,
        market_spread_pct: float,
    ) -> Trade:
        """Simulate execution with realistic slippage model."""
        slippage = market_spread_pct / 2  # Simple model: half spread as slippage
        executed_price = request.target_price * (1 + slippage if request.side == "buy" else 1 - slippage)

        async with db_session() as session:
            trade = Trade(
                market_id=request.market_id,
                condition_id=request.condition_id,
                side=request.side,
                outcome=request.outcome,
                source=request.source,
                status=TradeStatus.FILLED,
                size_usdc=request.size_usdc,
                target_price=request.target_price,
                executed_price=round(executed_price, 4),
                slippage_pct=round(slippage, 4),
                max_slippage_pct=request.max_slippage_pct,
                is_paper=True,
                executed_at=datetime.now(timezone.utc),
                risk_approved=True,
                ai_confidence=request.ai_confidence,
                ai_size_modifier=request.ai_size_modifier,
                ai_decision=request.ai_decision,
                ai_reasoning=request.ai_reasoning,
                copied_wallet=request.copied_wallet,
            )
            session.add(trade)

        logger.info(
            "paper_trade_executed",
            condition_id=request.condition_id,
            side=request.side,
            size_usdc=request.size_usdc,
            executed_price=executed_price,
            slippage=slippage,
            warnings=risk_result.warnings,
        )
        return trade

    async def _live_execute(
        self,
        request: TradeRequest,
        risk_result: RiskCheckResult,
    ) -> Trade:
        """Place a real order on Polymarket CLOB."""
        logger.info(
            "live_trade_submitting",
            condition_id=request.condition_id,
            size_usdc=request.size_usdc,
            target_price=request.target_price,
        )

        order_result = await self._client.place_order(
            token_id=request.condition_id,
            price=request.target_price,
            size=request.size_usdc,
            side=request.side,
        )

        async with db_session() as session:
            trade = Trade(
                market_id=request.market_id,
                condition_id=request.condition_id,
                side=request.side,
                outcome=request.outcome,
                source=request.source,
                status=TradeStatus.SUBMITTED if order_result else TradeStatus.FAILED,
                size_usdc=request.size_usdc,
                target_price=request.target_price,
                max_slippage_pct=request.max_slippage_pct,
                is_paper=False,
                order_id=order_result.get("orderID") if order_result else None,
                executed_at=datetime.now(timezone.utc) if order_result else None,
                risk_approved=True,
                ai_confidence=request.ai_confidence,
                ai_size_modifier=request.ai_size_modifier,
                ai_decision=request.ai_decision,
                ai_reasoning=request.ai_reasoning,
                copied_wallet=request.copied_wallet,
            )
            session.add(trade)

        return trade

    async def _record_trade(
        self,
        request: TradeRequest,
        risk_result: RiskCheckResult,
        is_paper: bool,
    ) -> Trade:
        """Record a rejected trade — always stored for audit trail."""
        async with db_session() as session:
            trade = Trade(
                market_id=request.market_id,
                condition_id=request.condition_id,
                side=request.side,
                outcome=request.outcome,
                source=request.source,
                status=TradeStatus.RISK_REJECTED,
                size_usdc=request.size_usdc,
                target_price=request.target_price,
                max_slippage_pct=request.max_slippage_pct,
                is_paper=is_paper,
                risk_approved=False,
                risk_rejection_reason=risk_result.rejection_reason,
                ai_confidence=request.ai_confidence,
                ai_size_modifier=request.ai_size_modifier,
                ai_decision=request.ai_decision,
                ai_reasoning=request.ai_reasoning,
            )
            session.add(trade)

        return trade

    async def _publish_trade_event(self, trade: Trade) -> None:
        """Notify all frontends of trade execution."""
        event = {
            "trade_id": trade.id,
            "condition_id": trade.condition_id,
            "side": trade.side,
            "outcome": trade.outcome,
            "size_usdc": trade.size_usdc,
            "status": trade.status,
            "executed_price": trade.executed_price,
            "is_paper": trade.is_paper,
            "ai_confidence": trade.ai_confidence,
            "ai_decision": trade.ai_decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await pubsub.publish("trade_executed", event)


_execution_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine
