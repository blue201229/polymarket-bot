"""
Strategy Runner — orchestrates all strategies with AI filtering.

For each market tick:
1. Run all enabled strategies (deterministic analysis)
2. For signals: run AI trade filter (advisory)
3. Apply AI size modifier if confidence is high
4. Submit to execution engine
5. Record signal + AI decision in DB
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from src.core.config import settings
from src.core.database import db_session
from src.core.logging import get_logger
from src.models.signal import Signal
from src.services.strategies.base import BaseStrategy, StrategyConfig, StrategySignal
from src.services.strategies.momentum import MomentumStrategy
from src.services.strategies.arbitrage import ArbitrageStrategy
from src.services.execution_engine import ExecutionEngine, TradeRequest, get_execution_engine
from src.ai.trade_filter import filter_signal

logger = get_logger(__name__)


def _build_default_strategies() -> List[BaseStrategy]:
    return [
        MomentumStrategy(StrategyConfig(
            name="momentum",
            base_size_usdc=settings.max_position_size_usdc * 0.3,
            min_ai_score=5.0,
            use_ai_filter=True,
        )),
        ArbitrageStrategy(StrategyConfig(
            name="arbitrage",
            base_size_usdc=settings.max_position_size_usdc * 0.5,
            min_ai_score=4.0,
            use_ai_filter=False,  # Arb is purely mathematical — AI adds less value
        )),
    ]


class StrategyRunner:

    def __init__(
        self,
        strategies: Optional[List[BaseStrategy]] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        self._strategies = strategies or _build_default_strategies()
        self._execution = execution_engine or get_execution_engine()
        self._current_positions_count = 0
        self._current_total_exposure = 0.0

    async def process_market(self, market: Dict[str, Any]) -> List[Signal]:
        """
        Run all strategies against a market update and execute qualifying signals.
        """
        generated_signals = []

        for strategy in self._strategies:
            if not strategy.config.enabled:
                continue

            try:
                raw_signal = await strategy.analyze(market)
            except Exception as e:
                logger.error("strategy_analysis_error", strategy=strategy.name(), error=str(e))
                continue

            if raw_signal is None:
                continue

            db_signal = await self._process_signal(raw_signal, market, strategy)
            if db_signal:
                generated_signals.append(db_signal)
                strategy.set_cooldown(market.get("condition_id", ""))

        return generated_signals

    async def _process_signal(
        self,
        signal: StrategySignal,
        market: Dict[str, Any],
        strategy: BaseStrategy,
    ) -> Optional[Signal]:
        """
        Apply AI filter, record signal, and optionally execute.
        """
        ai_result = None
        ai_override = False

        # AI filter (advisory — only if strategy enables it)
        if strategy.config.use_ai_filter and settings.ai_available:
            signal_data = {
                "strategy": signal.strategy,
                "side": signal.side,
                "outcome": signal.outcome,
                "target_price": signal.target_price,
                "suggested_size_usdc": signal.suggested_size_usdc,
                "strategy_win_rate": strategy.win_rate(),
                "strategy_trade_count": strategy._trade_count,
            }
            ai_result = await filter_signal(signal_data, market)

            # If AI says skip and confidence is very low — record but don't execute
            if (
                ai_result
                and ai_result.get("decision") == "skip"
                and ai_result.get("confidence", 1.0) < strategy.config.ai_min_confidence
            ):
                logger.info(
                    "signal_ai_skipped",
                    strategy=signal.strategy,
                    condition_id=signal.condition_id[:12],
                    ai_confidence=ai_result.get("confidence"),
                    reason=ai_result.get("key_concern"),
                )

                # Still record the signal for analysis
                db_signal = await self._save_signal(signal, ai_result, acted_on=False, skip_reason="ai_low_confidence")
                return db_signal

        # Apply AI size modifier
        final_size = signal.suggested_size_usdc
        if ai_result and ai_result.get("size_modifier"):
            final_size = signal.suggested_size_usdc * ai_result["size_modifier"]
            if final_size != signal.suggested_size_usdc:
                logger.info(
                    "ai_size_modifier_applied",
                    original=signal.suggested_size_usdc,
                    modified=round(final_size, 2),
                    modifier=ai_result["size_modifier"],
                )

        # Execute
        request = TradeRequest(
            condition_id=signal.condition_id,
            market_id=market.get("id", signal.condition_id),
            side=signal.side,
            outcome=signal.outcome,
            source=signal.strategy,
            size_usdc=final_size,
            target_price=signal.target_price,
            ai_confidence=ai_result.get("confidence") if ai_result else None,
            ai_size_modifier=ai_result.get("size_modifier") if ai_result else None,
            ai_decision=ai_result.get("decision") if ai_result else None,
            ai_reasoning=ai_result.get("reasoning") if ai_result else None,
        )

        trade = await self._execution.execute(
            request,
            market_liquidity=market.get("liquidity", 0),
            market_spread_pct=market.get("spread_pct", 0.1),
            current_positions_count=self._current_positions_count,
            current_total_exposure_usdc=self._current_total_exposure,
        )

        db_signal = await self._save_signal(
            signal,
            ai_result,
            acted_on=trade.risk_approved,
            skip_reason=trade.risk_rejection_reason,
            trade_id=trade.id,
        )

        if trade.risk_approved:
            self._current_positions_count += 1
            self._current_total_exposure += final_size

        return db_signal

    async def _save_signal(
        self,
        signal: StrategySignal,
        ai_result: Optional[Dict[str, Any]],
        acted_on: bool,
        skip_reason: Optional[str] = None,
        trade_id: Optional[str] = None,
    ) -> Signal:
        async with db_session() as session:
            db_signal = Signal(
                strategy=signal.strategy,
                condition_id=signal.condition_id,
                market_question=signal.market_data.get("question", "")[:200],
                side=signal.side,
                outcome=signal.outcome,
                target_price=signal.target_price,
                suggested_size_usdc=signal.suggested_size_usdc,
                spread_at_signal=signal.market_data.get("spread_pct"),
                liquidity_at_signal=signal.market_data.get("liquidity"),
                acted_on=acted_on,
                trade_id=trade_id,
                skip_reason=skip_reason,
                ai_confidence=ai_result.get("confidence") if ai_result else None,
                ai_size_modifier=ai_result.get("size_modifier") if ai_result else None,
                ai_decision=ai_result.get("decision") if ai_result else None,
                ai_reasoning=ai_result.get("reasoning") if ai_result else None,
            )
            session.add(db_signal)

        return db_signal
