from __future__ import annotations

from typing import Any, Optional

from backend.src.core.logging import get_logger
from backend.src.services.strategies.base import BaseStrategy, StrategySignal

logger = get_logger("strategies.momentum")


class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy: follow strong directional price moves.

    Looks for:
    - Significant price change in short period
    - Volume confirmation
    - Trend continuation potential
    """

    def __init__(
        self,
        min_momentum: float = 0.03,
        volume_confirmation_ratio: float = 1.5,
        base_size: float = 8.0,
        trailing_stop: float = 0.05,
    ) -> None:
        super().__init__(name="momentum")
        self.min_momentum = min_momentum
        self.volume_confirmation_ratio = volume_confirmation_ratio
        self.base_size = base_size
        self.trailing_stop = trailing_stop

    async def evaluate(self, market_data: dict[str, Any]) -> Optional[StrategySignal]:
        outcomes = market_data.get("outcomes", [])
        if not outcomes:
            return None

        for outcome_data in outcomes:
            price = float(outcome_data.get("price", 0))
            prev_price = float(outcome_data.get("previous_price", 0))

            if prev_price <= 0 or price <= 0:
                continue

            price_change = price - prev_price
            pct_change = price_change / prev_price

            if abs(pct_change) < self.min_momentum:
                continue

            # Volume confirmation
            volume_24h = float(market_data.get("volume_24h", 0))
            avg_volume = float(market_data.get("avg_daily_volume", volume_24h))
            volume_ratio = volume_24h / avg_volume if avg_volume > 0 else 0

            if volume_ratio < self.volume_confirmation_ratio:
                continue

            # Only trade in direction of momentum
            side = "buy" if pct_change > 0 else "sell"

            if side == "sell":
                continue  # only buy for simplicity in v1

            if price > 0.92 or price < 0.05:
                continue

            confidence = min(1.0, abs(pct_change) / 0.10)
            size = self.base_size * min(2.0, volume_ratio / self.volume_confirmation_ratio)

            return StrategySignal(
                market_id=market_data.get("market_id", ""),
                condition_id=market_data.get("condition_id", ""),
                token_id=outcome_data.get("token_id", ""),
                outcome=outcome_data.get("outcome", ""),
                side=side,
                price=price,
                size=size,
                strategy=self.name,
                confidence=confidence,
                context={
                    "momentum": pct_change,
                    "volume_ratio": volume_ratio,
                    "question": market_data.get("question", ""),
                    "volume_24h": volume_24h,
                    "liquidity": market_data.get("liquidity", 0),
                },
                reason=f"Momentum {pct_change:+.2%}, volume {volume_ratio:.1f}x avg",
            )

        return None

    async def should_close(
        self, position: dict[str, Any], market_data: dict[str, Any]
    ) -> Optional[StrategySignal]:
        entry_price = position.get("avg_entry_price", 0)
        current_price = position.get("current_price", 0)
        high_water = position.get("high_water_mark", current_price)

        if current_price <= 0:
            return None

        # Trailing stop
        drawdown_from_peak = high_water - current_price
        if drawdown_from_peak >= self.trailing_stop:
            return StrategySignal(
                market_id=position.get("market_id", ""),
                condition_id=position.get("condition_id", ""),
                token_id=position.get("token_id", ""),
                outcome=position.get("outcome", ""),
                side="sell",
                price=current_price,
                size=position.get("size", 0),
                strategy=self.name,
                confidence=0.8,
                reason=f"Trailing stop: peak={high_water:.3f}, current={current_price:.3f}",
            )

        return None
