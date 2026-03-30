"""
Wallet Watcher — monitors tracked wallets and triggers copy trade logic.

Phase 3 feature. Polls wallet trade history and:
1. Detects new trades from high-quality wallets
2. Runs AI wallet analysis to update quality scores
3. Generates copy trade signals for qualifying wallets
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import db_session
from src.core.logging import get_logger
from src.core.redis_client import pubsub
from src.data.polymarket_client import get_polymarket_client
from src.models.wallet import Wallet, WalletTrade
from src.models.signal import Signal
from src.ai.wallet_analysis import analyze_wallet

logger = get_logger(__name__)


class WalletWatcher:

    def __init__(self):
        self._client = get_polymarket_client()
        self._running = False
        self._poll_interval = 60  # seconds

    async def start(self) -> None:
        self._running = True
        logger.info("wallet_watcher_started")
        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error("wallet_watcher_error", error=str(e))
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False

    async def _poll_cycle(self) -> None:
        async with db_session() as session:
            result = await session.execute(
                select(Wallet).where(Wallet.is_tracked == True)
            )
            wallets = list(result.scalars().all())

        logger.debug("wallet_watcher_polling", wallet_count=len(wallets))

        for wallet in wallets:
            await self._process_wallet(wallet)

    async def _process_wallet(self, wallet: Wallet) -> None:
        """Fetch new trades for a wallet and process them."""
        trades = await self._client.get_trades(maker=wallet.address, limit=50)

        if not trades:
            return

        new_trades = await self._filter_new_trades(wallet, trades)

        if new_trades:
            await self._store_wallet_trades(wallet, new_trades)
            await self._update_wallet_stats(wallet, new_trades)

            # Re-analyze wallet if enough new data
            if wallet.total_trades >= 10 and len(new_trades) > 0:
                await self._reanalyze_wallet(wallet)

            # Generate copy trade signals for qualifying wallets
            if wallet.copy_trade_enabled and wallet.ai_quality_score and wallet.ai_quality_score >= 6.5:
                for trade in new_trades:
                    await self._generate_copy_signal(wallet, trade)

    async def _filter_new_trades(self, wallet: Wallet, trades: List[Dict]) -> List[Dict]:
        """Return only trades not yet stored."""
        async with db_session() as session:
            existing_hashes = set()
            result = await session.execute(
                select(WalletTrade.tx_hash).where(WalletTrade.wallet_id == wallet.id)
            )
            existing_hashes = {row[0] for row in result.fetchall() if row[0]}

        return [t for t in trades if t.get("transactionHash") not in existing_hashes]

    async def _store_wallet_trades(self, wallet: Wallet, trades: List[Dict]) -> None:
        async with db_session() as session:
            for t in trades:
                wt = WalletTrade(
                    wallet_id=wallet.id,
                    condition_id=t.get("market", ""),
                    outcome=t.get("outcome", "Yes"),
                    side=t.get("side", "buy").lower(),
                    price=float(t.get("price", 0)),
                    size=float(t.get("size", 0)),
                    timestamp=datetime.now(timezone.utc),
                    tx_hash=t.get("transactionHash"),
                )
                session.add(wt)

    async def _update_wallet_stats(self, wallet: Wallet, new_trades: List[Dict]) -> None:
        async with db_session() as session:
            db_wallet = await session.get(Wallet, wallet.id)
            if not db_wallet:
                return
            db_wallet.total_trades += len(new_trades)
            db_wallet.last_trade_at = datetime.now(timezone.utc)

    async def _reanalyze_wallet(self, wallet: Wallet) -> None:
        """Re-run AI wallet analysis."""
        async with db_session() as session:
            result = await session.execute(
                select(WalletTrade)
                .where(WalletTrade.wallet_id == wallet.id)
                .order_by(WalletTrade.timestamp.desc())
                .limit(100)
            )
            trade_history = [
                {
                    "condition_id": t.condition_id,
                    "side": t.side,
                    "outcome": t.outcome,
                    "price": t.price,
                    "size": t.size,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                }
                for t in result.scalars().all()
            ]

        wallet_data = {
            "address": wallet.address,
            "total_trades": wallet.total_trades,
            "win_rate": wallet.win_rate or 0.5,
            "avg_pnl_pct": wallet.avg_pnl_pct or 0,
            "total_volume_usdc": wallet.total_volume_usdc,
            "first_seen_at": wallet.first_seen_at.isoformat() if wallet.first_seen_at else None,
        }

        analysis = await analyze_wallet(wallet_data, trade_history, wallet_id=wallet.id)

        async with db_session() as session:
            db_wallet = await session.get(Wallet, wallet.id)
            if not db_wallet:
                return
            db_wallet.ai_quality_score = analysis.get("quality_score")
            db_wallet.ai_strategy_class = analysis.get("strategy_class")
            db_wallet.ai_confidence = analysis.get("confidence")
            db_wallet.ai_analysis_summary = analysis.get("summary")
            db_wallet.ai_analyzed_at = datetime.now(timezone.utc)

        logger.info(
            "wallet_reanalyzed",
            address=wallet.address,
            score=analysis.get("quality_score"),
            strategy=analysis.get("strategy_class"),
        )

        await pubsub.publish("wallet_event", {
            "type": "analysis_updated",
            "wallet": wallet.address,
            "quality_score": analysis.get("quality_score"),
            "strategy_class": analysis.get("strategy_class"),
        })

    async def _generate_copy_signal(self, wallet: Wallet, trade: Dict[str, Any]) -> None:
        """Create a copy trade signal based on a wallet's detected trade."""
        size = float(trade.get("size", 0)) * wallet.copy_trade_size_pct
        size = min(size, wallet.copy_trade_max_size_usdc)

        if size < 1.0:
            return

        async with db_session() as session:
            signal = Signal(
                strategy="copy_trade",
                condition_id=trade.get("market", ""),
                side=trade.get("side", "buy"),
                outcome=trade.get("outcome", "Yes"),
                target_price=float(trade.get("price", 0)),
                suggested_size_usdc=size,
            )
            session.add(signal)

        logger.info(
            "copy_trade_signal_generated",
            wallet=wallet.address,
            condition_id=trade.get("market"),
            size=size,
        )

        await pubsub.publish("ai_signal", {
            "type": "copy_trade",
            "wallet": wallet.address,
            "wallet_score": wallet.ai_quality_score,
            "condition_id": trade.get("market"),
            "side": trade.get("side"),
            "size_usdc": size,
        })
