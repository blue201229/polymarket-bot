from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.ai.optimizer import OptimizationResult, ParameterOptimizer
from backend.src.ai.post_trade import PostTradeAnalyzer, PostTradeReport
from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.logging import get_logger
from backend.src.models.trade import Trade, TradeStatus

logger = get_logger("services.performance")


class PerformanceService:
    """
    Aggregates trading performance metrics and coordinates AI-powered
    optimization and post-trade analysis.

    Deterministic: metric computation, PnL tracking
    AI-assisted: parameter optimization suggestions, trade pattern analysis
    """

    def __init__(
        self,
        optimizer: Optional[ParameterOptimizer] = None,
        post_trade: Optional[PostTradeAnalyzer] = None,
    ) -> None:
        self._optimizer = optimizer or ParameterOptimizer()
        self._post_trade = post_trade or PostTradeAnalyzer()

    async def get_summary(self, days: int = 7) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        async with get_session() as session:
            trades = await self._fetch_trades(session, since)

        if not trades:
            return {
                "window_days": days,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "net_pnl": 0,
                "avg_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "max_drawdown": 0,
                "strategies": {},
                "trades": [],
            }

        pnls = [t.pnl or 0 for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        # Calculate max drawdown
        cumulative = []
        running = 0
        for p in pnls:
            running += p
            cumulative.append(running)
        peak = 0
        max_dd = 0
        for c in cumulative:
            if c > peak:
                peak = c
            dd = peak - c
            if dd > max_dd:
                max_dd = dd

        # Strategy breakdown
        strategies: dict[str, dict[str, Any]] = {}
        for t in trades:
            s = t.strategy
            if s not in strategies:
                strategies[s] = {"trades": 0, "wins": 0, "pnl": 0.0}
            strategies[s]["trades"] += 1
            strategies[s]["pnl"] += t.pnl or 0
            if (t.pnl or 0) > 0:
                strategies[s]["wins"] += 1

        for s in strategies:
            total = strategies[s]["trades"]
            strategies[s]["win_rate"] = (
                (strategies[s]["wins"] / total * 100) if total > 0 else 0
            )

        trade_details = [
            {
                "strategy": t.strategy,
                "side": t.side,
                "outcome": t.outcome,
                "entry_price": t.price,
                "exit_price": t.filled_price or t.price,
                "pnl": t.pnl or 0,
                "hold_hours": (
                    (t.closed_at - t.created_at).total_seconds() / 3600
                    if t.closed_at
                    else 0
                ),
                "ai_confidence": t.ai_confidence,
            }
            for t in trades[:30]
        ]

        return {
            "window_days": days,
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(trades) * 100 if trades else 0,
            "net_pnl": sum(pnls),
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
            "avg_win": sum(wins) / len(wins) if wins else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "best_trade": max(pnls) if pnls else 0,
            "worst_trade": min(pnls) if pnls else 0,
            "max_drawdown": max_dd,
            "strategies": strategies,
            "trades": trade_details,
        }

    async def run_optimization(
        self,
        current_params: Optional[dict[str, Any]] = None,
        days: int = 7,
    ) -> OptimizationResult:
        """Run AI parameter optimization based on recent performance."""
        summary = await self.get_summary(days=days)

        params = current_params or {
            "slippage_bps": settings.default_slippage_bps,
            "entry_threshold": 0.6,
            "max_position_size": settings.max_position_size_usd,
            "cooldown_seconds": 30,
            "min_liquidity": 500,
            "min_volume_24h": 100,
        }

        performance_data = {
            **params,
            **summary,
            "avg_slippage": 0,
            "skipped_liquidity": 0,
            "skipped_spread": 0,
            "avg_market_volume": 0,
            "avg_spread": 0,
            "active_markets": 0,
        }

        result = await self._optimizer.optimize(performance_data)
        logger.info(
            "Optimization completed",
            suggestions=len(result.suggestions),
            confidence=result.confidence,
        )
        return result

    async def run_post_trade_analysis(self, days: int = 7) -> PostTradeReport:
        """Run AI post-trade analysis on recent performance."""
        summary = await self.get_summary(days=days)
        report = await self._post_trade.analyze(summary)
        logger.info(
            "Post-trade analysis completed",
            insights=len(report.insights),
            top_improvement=report.top_improvement[:80] if report.top_improvement else "N/A",
        )
        return report

    async def get_ai_impact_report(self, days: int = 30) -> dict[str, Any]:
        """Compare AI-assisted vs non-AI trades to measure AI impact."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        async with get_session() as session:
            all_trades = await self._fetch_trades(session, since)

        ai_trades = [t for t in all_trades if t.ai_confidence is not None]
        non_ai_trades = [t for t in all_trades if t.ai_confidence is None]

        def calc_stats(trades: list) -> dict[str, Any]:
            if not trades:
                return {"count": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0}
            pnls = [t.pnl or 0 for t in trades]
            wins = len([p for p in pnls if p > 0])
            return {
                "count": len(trades),
                "win_rate": wins / len(trades) * 100 if trades else 0,
                "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
                "total_pnl": sum(pnls),
            }

        return {
            "window_days": days,
            "ai_assisted": calc_stats(ai_trades),
            "non_ai": calc_stats(non_ai_trades),
            "ai_skip_count": len([
                t for t in all_trades
                if t.ai_approved is False and t.ai_skip_reason
            ]),
        }

    async def _fetch_trades(self, session: AsyncSession, since: datetime) -> list[Trade]:
        result = await session.execute(
            select(Trade)
            .where(
                Trade.created_at >= since,
                Trade.status.in_([TradeStatus.FILLED, TradeStatus.PAPER]),
            )
            .order_by(Trade.created_at.desc())
        )
        return list(result.scalars().all())
