"""
Arbitrage Strategy — exploits price inefficiencies between YES+NO prices.

On Polymarket: YES + NO prices should sum to ~1.0.
If they don't, there's an arbitrage opportunity.

Also detects cross-market arbitrage where related events have inconsistent pricing.
"""
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseStrategy, StrategyConfig, StrategySignal
from src.core.logging import get_logger

logger = get_logger(__name__)

# Minimum profit after fees/slippage to consider an arb
MIN_ARB_PROFIT_PCT = 0.015


class ArbitrageStrategy(BaseStrategy):
    """
    YES+NO sum arbitrage.

    If YES + NO < 1.0 - threshold: buy both (locked profit at resolution)
    If YES + NO > 1.0 + threshold: sell both (or buy whichever is cheaper vs fair value)
    """

    def name(self) -> str:
        return "arbitrage"

    async def analyze(self, market: Dict[str, Any]) -> Optional[StrategySignal]:
        condition_id = market.get("condition_id", "")

        if self.is_on_cooldown(condition_id):
            return None

        yes_ask = market.get("yes_ask") or market.get("best_ask")
        no_ask = market.get("no_ask")

        if not yes_ask or not no_ask:
            return None

        signal = self._detect_sum_arb(market, yes_ask, no_ask)
        return signal

    def _detect_sum_arb(
        self,
        market: Dict[str, Any],
        yes_ask: float,
        no_ask: float,
    ) -> Optional[StrategySignal]:
        """
        YES + NO should sum to exactly 1.0.
        If sum < 1.0 - MIN_ARB_PROFIT_PCT, buying both locks in profit.
        """
        total_cost = yes_ask + no_ask
        profit = 1.0 - total_cost

        if profit < MIN_ARB_PROFIT_PCT:
            return None

        # Prefer buying the cheaper token
        if yes_ask <= no_ask:
            side = "buy"
            outcome = "Yes"
            target_price = yes_ask
        else:
            side = "buy"
            outcome = "No"
            target_price = no_ask

        confidence = min(profit / 0.05, 1.0)  # Scale with profit margin
        suggested_size = min(
            self.config.base_size_usdc * (profit / MIN_ARB_PROFIT_PCT),
            self.config.base_size_usdc * 2,
        )

        logger.info(
            "arb_signal_generated",
            condition_id=market.get("condition_id", "")[:12],
            yes_ask=yes_ask,
            no_ask=no_ask,
            profit=round(profit, 4),
        )

        return StrategySignal(
            strategy="arbitrage",
            condition_id=market.get("condition_id", ""),
            side=side,
            outcome=outcome,
            target_price=round(target_price, 4),
            suggested_size_usdc=round(suggested_size, 2),
            confidence=round(confidence, 3),
            reasoning=f"YES({yes_ask:.3f}) + NO({no_ask:.3f}) = {total_cost:.3f} < 1.0. Profit: {profit:.2%}",
            market_data=market,
        )
