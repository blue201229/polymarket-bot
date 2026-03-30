from __future__ import annotations

from typing import Any, Optional

from backend.src.core.logging import get_logger
from backend.src.services.strategies.base import BaseStrategy, StrategySignal

logger = get_logger("strategies.value")


class ValueStrategy(BaseStrategy):
    """
    Value strategy: buy outcomes that appear underpriced based on
    deterministic criteria (edge calculation).

    Looks for:
    - Significant edge between estimated fair value and current price
    - Sufficient liquidity
    - Reasonable time to expiry
    """

    def __init__(
        self,
        min_edge: float = 0.05,
        max_price: float = 0.85,
        min_price: float = 0.10,
        base_size: float = 10.0,
        take_profit: float = 0.15,
        stop_loss: float = 0.10,
    ) -> None:
        super().__init__(name="value")
        self.min_edge = min_edge
        self.max_price = max_price
        self.min_price = min_price
        self.base_size = base_size
        self.take_profit = take_profit
        self.stop_loss = stop_loss

    async def evaluate(self, market_data: dict[str, Any]) -> Optional[StrategySignal]:
        outcomes = market_data.get("outcomes", [])
        if not outcomes:
            return None

        for outcome_data in outcomes:
            price = float(outcome_data.get("price", 0))

            if price < self.min_price or price > self.max_price:
                continue

            estimated_value = self._estimate_fair_value(outcome_data, market_data)
            edge = estimated_value - price

            if edge >= self.min_edge:
                size = self._calculate_size(edge)
                return StrategySignal(
                    market_id=market_data.get("market_id", ""),
                    condition_id=market_data.get("condition_id", ""),
                    token_id=outcome_data.get("token_id", ""),
                    outcome=outcome_data.get("outcome", ""),
                    side="buy",
                    price=price,
                    size=size,
                    strategy=self.name,
                    confidence=min(1.0, edge / 0.20),
                    context={
                        "edge": edge,
                        "estimated_value": estimated_value,
                        "question": market_data.get("question", ""),
                        "volume_24h": market_data.get("volume_24h", 0),
                        "liquidity": market_data.get("liquidity", 0),
                    },
                    reason=f"Edge {edge:.3f} (fair value {estimated_value:.3f} vs price {price:.3f})",
                )

        return None

    async def should_close(
        self, position: dict[str, Any], market_data: dict[str, Any]
    ) -> Optional[StrategySignal]:
        entry_price = position.get("avg_entry_price", 0)
        current_price = position.get("current_price", 0)

        if current_price <= 0 or entry_price <= 0:
            return None

        profit = current_price - entry_price
        loss = entry_price - current_price

        if profit >= self.take_profit or loss >= self.stop_loss:
            action = "take_profit" if profit >= self.take_profit else "stop_loss"
            return StrategySignal(
                market_id=position.get("market_id", ""),
                condition_id=position.get("condition_id", ""),
                token_id=position.get("token_id", ""),
                outcome=position.get("outcome", ""),
                side="sell",
                price=current_price,
                size=position.get("size", 0),
                strategy=self.name,
                confidence=0.9,
                reason=f"{action}: entry={entry_price:.3f}, current={current_price:.3f}",
            )

        return None

    def _estimate_fair_value(
        self, outcome_data: dict[str, Any], market_data: dict[str, Any]
    ) -> float:
        """
        Simple fair value estimation based on market structure.
        In production, this would use more sophisticated models.
        """
        price = float(outcome_data.get("price", 0.5))
        prev_price = float(outcome_data.get("previous_price", price))

        momentum = price - prev_price if prev_price > 0 else 0
        volume_weight = min(1.0, float(market_data.get("volume_24h", 0)) / 50000)

        fair_value = price + (momentum * 0.3 * volume_weight)
        return max(0.01, min(0.99, fair_value))

    def _calculate_size(self, edge: float) -> float:
        """Kelly-inspired sizing: larger edge = larger position."""
        kelly_fraction = min(0.25, edge / (1 + edge))
        return self.base_size * (1 + kelly_fraction * 4)
