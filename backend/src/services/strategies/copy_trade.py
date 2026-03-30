from __future__ import annotations

from typing import Any, Optional

from backend.src.core.logging import get_logger
from backend.src.services.strategies.base import BaseStrategy, StrategySignal

logger = get_logger("strategies.copy_trade")


class CopyTradeStrategy(BaseStrategy):
    """
    Copy trade strategy: replicate trades from high-quality wallets.

    This strategy processes signals from the WalletWatcher service.
    AI wallet quality scoring determines whether a wallet's trades
    should be copied.

    Pipeline:
    1. WalletWatcher detects new transaction
    2. AI quality check on wallet (cached)
    3. If wallet passes quality threshold, generate signal
    4. Signal goes through normal execution pipeline (AI filter + risk)
    """

    def __init__(
        self,
        min_wallet_quality: float = 6.0,
        min_confidence: float = 0.5,
        size_multiplier: float = 0.5,
        max_delay_seconds: int = 120,
    ) -> None:
        super().__init__(name="copy_trade")
        self.min_wallet_quality = min_wallet_quality
        self.min_confidence = min_confidence
        self.size_multiplier = size_multiplier
        self.max_delay_seconds = max_delay_seconds

    async def evaluate(self, market_data: dict[str, Any]) -> Optional[StrategySignal]:
        """
        This strategy doesn't scan markets — it's driven by wallet events.
        See evaluate_copy_signal() for the actual entry point.
        """
        return None

    async def evaluate_copy_signal(
        self,
        wallet_quality: float,
        wallet_strategy: str,
        copy_data: dict[str, Any],
    ) -> Optional[StrategySignal]:
        if wallet_quality < self.min_wallet_quality:
            logger.debug(
                "Wallet quality below threshold",
                quality=wallet_quality,
                threshold=self.min_wallet_quality,
            )
            return None

        price = float(copy_data.get("price", 0))
        size = float(copy_data.get("size", 0)) * self.size_multiplier

        if price <= 0 or size <= 0:
            return None

        confidence = min(1.0, wallet_quality / 10.0)
        if confidence < self.min_confidence:
            return None

        return StrategySignal(
            market_id=copy_data.get("market_id", ""),
            condition_id=copy_data.get("condition_id", ""),
            token_id=copy_data.get("token_id", ""),
            outcome=copy_data.get("outcome", ""),
            side=copy_data.get("side", "buy"),
            price=price,
            size=size,
            strategy=f"copy_{wallet_strategy}",
            confidence=confidence,
            context={
                "source_wallet": copy_data.get("source_wallet", ""),
                "wallet_quality": wallet_quality,
                "wallet_strategy": wallet_strategy,
                "original_size": copy_data.get("size", 0),
            },
            reason=f"Copy trade from {wallet_strategy} wallet (quality: {wallet_quality:.1f})",
        )

    async def should_close(
        self, position: dict[str, Any], market_data: dict[str, Any]
    ) -> Optional[StrategySignal]:
        entry_price = position.get("avg_entry_price", 0)
        current_price = position.get("current_price", 0)

        if current_price <= 0 or entry_price <= 0:
            return None

        loss = entry_price - current_price
        if loss >= 0.12:
            return StrategySignal(
                market_id=position.get("market_id", ""),
                condition_id=position.get("condition_id", ""),
                token_id=position.get("token_id", ""),
                outcome=position.get("outcome", ""),
                side="sell",
                price=current_price,
                size=position.get("size", 0),
                strategy=self.name,
                confidence=0.7,
                reason=f"Copy stop-loss: entry={entry_price:.3f}, current={current_price:.3f}",
            )

        return None
