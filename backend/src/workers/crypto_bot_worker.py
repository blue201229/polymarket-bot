"""
Crypto Bot Worker — short-duration crypto prediction market bot.

Trades crypto-related Polymarket markets (BTC/ETH price predictions)
using technical analysis signals with AI filtering.

Phase 4 feature.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.data.polymarket_client import get_polymarket_client
from src.services.strategy_runner import StrategyRunner
from src.services.strategies.base import StrategyConfig
from src.services.strategies.momentum import MomentumStrategy

logger = get_logger(__name__)

CRYPTO_KEYWORDS = ["bitcoin", "ethereum", "btc", "eth", "crypto", "coinbase", "solana"]


class CryptoBotWorker:
    """
    Specialized strategy runner for crypto prediction markets.

    Runs more frequently than general strategy runner (every 5 minutes)
    and targets only crypto-tagged markets.
    """

    def __init__(self):
        self._client = get_polymarket_client()
        self._runner = StrategyRunner(
            strategies=[
                MomentumStrategy(StrategyConfig(
                    name="crypto_momentum",
                    base_size_usdc=settings.max_position_size_usdc * 0.2,
                    min_ai_score=4.5,
                    entry_threshold=0.04,  # Tighter for crypto
                    cooldown_seconds=300,
                    use_ai_filter=True,
                )),
            ]
        )
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("crypto_bot_worker_starting")
        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error("crypto_bot_error", error=str(e))
            await asyncio.sleep(300)  # Every 5 minutes

    async def stop(self) -> None:
        self._running = False

    async def _run_cycle(self) -> None:
        crypto_markets = await self._get_crypto_markets()
        logger.info("crypto_bot_cycle", markets=len(crypto_markets))

        for market in crypto_markets:
            await self._runner.process_market(market)

    async def _get_crypto_markets(self) -> List[Dict[str, Any]]:
        """Fetch active crypto prediction markets."""
        from sqlalchemy import select, or_
        from src.core.database import db_session
        from src.models.market import Market

        async with db_session() as session:
            conditions = [Market.question.ilike(f"%{kw}%") for kw in CRYPTO_KEYWORDS]
            result = await session.execute(
                select(Market)
                .where(Market.active == True, Market.closed == False)
                .where(or_(*conditions))
                .limit(20)
            )
            markets = result.scalars().all()

        return [
            {
                "id": m.id,
                "condition_id": m.condition_id,
                "question": m.question,
                "best_bid": m.best_bid,
                "best_ask": m.best_ask,
                "spread_pct": m.spread_pct or 0.05,
                "volume_24h": m.volume_24h,
                "liquidity": m.liquidity,
                "ai_score": m.ai_score,
                "price_history": [],  # TODO: build from tick cache
            }
            for m in markets
        ]
