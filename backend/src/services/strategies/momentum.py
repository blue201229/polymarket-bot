"""
Momentum Strategy — buys outcome tokens showing strong directional price movement.

Logic:
1. Check recent price trend (deterministic)
2. Verify liquidity and spread conditions
3. Check AI market score (advisory gate)
4. Emit signal if conditions met
5. AI trade filter applied in strategy runner (not here)

This strategy is deterministic. AI is applied externally.
"""
from typing import Any, Dict, Optional

from .base import BaseStrategy, StrategyConfig, StrategySignal
from src.core.logging import get_logger

logger = get_logger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy: enter when price moves >X% in one direction
    with sufficient volume confirmation.
    """

    def name(self) -> str:
        return "momentum"

    async def analyze(self, market: Dict[str, Any]) -> Optional[StrategySignal]:
        condition_id = market.get("condition_id", "")

        if self.is_on_cooldown(condition_id):
            return None

        if not self._passes_base_filters(market):
            return None

        signal = self._detect_momentum(market)
        return signal

    def _passes_base_filters(self, market: Dict[str, Any]) -> bool:
        """Deterministic filters before any signal generation."""
        liquidity = market.get("liquidity", 0)
        spread_pct = market.get("spread_pct", 1.0)
        ai_score = market.get("ai_score")

        if liquidity < self.config.min_liquidity:
            return False
        if spread_pct > self.config.max_spread_pct:
            return False
        if ai_score is not None and ai_score < self.config.min_ai_score:
            return False

        return True

    def _detect_momentum(self, market: Dict[str, Any]) -> Optional[StrategySignal]:
        """
        Detect momentum signal from price history.

        Uses:
        - price_history: recent YES token prices
        - volume trend: increasing volume confirms momentum
        """
        price_history = market.get("price_history", [])
        if len(price_history) < 5:
            return None

        recent = price_history[-5:]
        start_price = recent[0]
        current_price = recent[-1]

        if start_price <= 0:
            return None

        move = (current_price - start_price) / start_price

        # Minimum edge threshold
        if abs(move) < self.config.entry_threshold:
            return None

        # Avoid extreme prices (already priced in)
        if current_price > 0.92 or current_price < 0.08:
            return None

        side = "buy"
        outcome = "Yes" if move > 0 else "No"
        target_price = current_price * 1.005  # Small buffer

        # Size scales with signal strength
        strength = min(abs(move) / self.config.entry_threshold, 2.0)
        suggested_size = self.config.base_size_usdc * min(strength, 1.5)

        # Strategy confidence based on move consistency
        consistency = sum(1 for i in range(1, len(recent)) if
                         (recent[i] > recent[i-1]) == (move > 0)) / (len(recent) - 1)
        confidence = 0.3 + (consistency * 0.4) + (min(abs(move) / 0.10, 1.0) * 0.3)

        logger.info(
            "momentum_signal_generated",
            condition_id=market.get("condition_id", "")[:12],
            move=round(move, 4),
            consistency=round(consistency, 2),
            confidence=round(confidence, 2),
        )

        return StrategySignal(
            strategy="momentum",
            condition_id=market.get("condition_id", ""),
            side=side,
            outcome=outcome,
            target_price=round(target_price, 4),
            suggested_size_usdc=round(suggested_size, 2),
            confidence=round(confidence, 3),
            reasoning=f"Price moved {move:.1%} over last {len(recent)} ticks with {consistency:.0%} consistency",
            market_data=market,
        )
