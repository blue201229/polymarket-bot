from __future__ import annotations

from typing import Any, Optional

from backend.src.core.logging import get_logger
from backend.src.services.strategies.base import BaseStrategy, StrategySignal

logger = get_logger("strategies.arbitrage")


class ArbitrageStrategy(BaseStrategy):
    """
    Arbitrage strategy for prediction markets.

    Identifies mispricing between complementary outcomes:
    - Binary markets: Yes + No should sum to ~1.00
    - If the sum deviates significantly, there's an arb opportunity
    - Also detects cross-market arbitrage when similar questions exist

    This is a deterministic strategy — AI is NOT used for the core logic,
    but AI scoring can filter which arb opportunities to prioritize.
    """

    def __init__(
        self,
        min_arb_bps: int = 30,
        min_liquidity: float = 1000.0,
        base_size: float = 20.0,
        max_price: float = 0.95,
    ) -> None:
        super().__init__(name="arbitrage")
        self.min_arb_bps = min_arb_bps
        self.min_liquidity = min_liquidity
        self.base_size = base_size
        self.max_price = max_price

    async def evaluate(self, market_data: dict[str, Any]) -> Optional[StrategySignal]:
        outcomes = market_data.get("outcomes", [])
        if len(outcomes) < 2:
            return None

        prices = [float(o.get("price", 0)) for o in outcomes]
        price_sum = sum(prices)

        # In a binary market, prices should sum to ~1.00
        overround = price_sum - 1.0
        arb_bps = int(abs(overround) * 10000)

        if arb_bps < self.min_arb_bps:
            return None

        liquidity = float(market_data.get("liquidity", 0))
        if liquidity < self.min_liquidity:
            return None

        if overround < 0:
            # Underpriced: buy both sides and profit at resolution
            cheapest = min(outcomes, key=lambda o: float(o.get("price", 1)))
            buy_price = float(cheapest.get("price", 0))

            if buy_price > self.max_price or buy_price <= 0:
                return None

            size = min(self.base_size, liquidity * 0.02)

            return StrategySignal(
                market_id=market_data.get("market_id", ""),
                condition_id=market_data.get("condition_id", ""),
                token_id=cheapest.get("token_id", ""),
                outcome=cheapest.get("outcome", ""),
                side="buy",
                price=buy_price,
                size=size,
                strategy=self.name,
                confidence=min(1.0, arb_bps / 100),
                context={
                    "arb_bps": arb_bps,
                    "price_sum": price_sum,
                    "overround": overround,
                    "question": market_data.get("question", ""),
                    "liquidity": liquidity,
                },
                reason=f"Underpriced arb: sum={price_sum:.4f}, edge={arb_bps}bps",
            )

        return None

    async def should_close(
        self, position: dict[str, Any], market_data: dict[str, Any]
    ) -> Optional[StrategySignal]:
        # Arb positions typically held to resolution
        # Close early only if the arb closes (prices converge)
        outcomes = market_data.get("outcomes", [])
        prices = [float(o.get("price", 0)) for o in outcomes]
        price_sum = sum(prices)

        # If prices have converged to fair value, exit
        if abs(price_sum - 1.0) < 0.005:
            current_price = float(
                next(
                    (o.get("price", 0) for o in outcomes
                     if o.get("token_id") == position.get("token_id")),
                    0,
                )
            )
            if current_price > position.get("avg_entry_price", 0):
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
                    reason="Arb closed: prices converged to fair value",
                )

        return None
