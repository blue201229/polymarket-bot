from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.ai.wallet_analysis import WalletAnalyzer, WalletProfile
from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger
from backend.src.models.wallet import WalletTransaction, WatchedWallet
from backend.src.utils.http_client import http_get

logger = get_logger("services.wallet_watcher")


class WalletWatcher:
    """
    Monitors watched wallets for new trading activity on Polymarket.

    Pipeline:
    1. Poll for new wallet transactions
    2. Record transactions in database
    3. If copy-trading enabled AND wallet passes AI quality check,
       emit signals for the execution engine
    4. Periodically re-analyze wallets using AI

    AI integration:
    - Wallet quality scoring
    - Strategy classification
    - Copy recommendation (strong_copy, selective_copy, avoid)
    """

    def __init__(self, analyzer: Optional[WalletAnalyzer] = None) -> None:
        self._analyzer = analyzer or WalletAnalyzer()
        self._poll_interval = 30  # seconds
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("Wallet watcher started")
        while self._running:
            try:
                await self._poll_all_wallets()
            except Exception as e:
                logger.error("Wallet polling error", error=str(e))
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("Wallet watcher stopped")

    async def add_wallet(
        self,
        address: str,
        label: Optional[str] = None,
        copy_enabled: bool = False,
        copy_size_multiplier: float = 1.0,
    ) -> WatchedWallet:
        async with get_session() as session:
            existing = await session.execute(
                select(WatchedWallet).where(WatchedWallet.address == address.lower())
            )
            wallet = existing.scalar_one_or_none()

            if wallet:
                wallet.label = label or wallet.label
                wallet.copy_enabled = copy_enabled
                wallet.copy_size_multiplier = copy_size_multiplier
                wallet.is_active = True
            else:
                wallet = WatchedWallet(
                    address=address.lower(),
                    label=label,
                    copy_enabled=copy_enabled,
                    copy_size_multiplier=copy_size_multiplier,
                )
                session.add(wallet)

            return wallet

    async def remove_wallet(self, address: str) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(WatchedWallet).where(WatchedWallet.address == address.lower())
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                wallet.is_active = False
                wallet.copy_enabled = False

    async def analyze_wallet(self, address: str) -> Optional[WalletProfile]:
        """Run AI analysis on a specific wallet."""
        async with get_session() as session:
            result = await session.execute(
                select(WatchedWallet).where(WatchedWallet.address == address.lower())
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                return None

            wallet_stats = await self._gather_wallet_stats(session, address.lower())
            profile = await self._analyzer.analyze_wallet(wallet_stats)

            wallet.ai_quality_score = profile.quality_score
            wallet.ai_strategy_class = profile.strategy_classification
            wallet.ai_confidence = profile.confidence
            wallet.ai_analysis = profile.reasoning
            wallet.ai_analyzed_at = datetime.now(timezone.utc)

            return profile

    async def _poll_all_wallets(self) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(WatchedWallet).where(
                    WatchedWallet.is_active == True
                )
            )
            wallets = result.scalars().all()

        for wallet in wallets:
            try:
                new_txs = await self._fetch_wallet_transactions(wallet.address)
                if new_txs:
                    await self._process_transactions(wallet, new_txs)
            except Exception as e:
                logger.error(
                    "Error polling wallet",
                    address=wallet.address[:10],
                    error=str(e),
                )

    async def _fetch_wallet_transactions(self, address: str) -> list[dict[str, Any]]:
        """Fetch recent transactions for a wallet from Polymarket/chain data."""
        try:
            url = f"{settings.polymarket_gamma_url}/activity"
            params = {"address": address, "limit": 50}
            return await http_get(url, params=params)
        except Exception:
            return []

    async def _process_transactions(
        self, wallet: WatchedWallet, transactions: list[dict[str, Any]]
    ) -> None:
        async with get_session() as session:
            for tx in transactions:
                tx_hash = tx.get("tx_hash", "")
                if tx_hash:
                    existing = await session.execute(
                        select(WalletTransaction).where(
                            WalletTransaction.tx_hash == tx_hash
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                wallet_tx = WalletTransaction(
                    wallet_address=wallet.address,
                    condition_id=tx.get("condition_id", ""),
                    token_id=tx.get("token_id"),
                    side=tx.get("side", "buy"),
                    size=float(tx.get("size", 0)),
                    price=float(tx.get("price", 0)),
                    tx_hash=tx_hash,
                    outcome=tx.get("outcome"),
                )
                session.add(wallet_tx)

                await event_bus.publish(
                    Events.WALLET_ACTIVITY,
                    wallet=wallet,
                    transaction=tx,
                )

                if wallet.copy_enabled:
                    await self._emit_copy_signal(wallet, tx)

    async def _emit_copy_signal(
        self, wallet: WatchedWallet, tx: dict[str, Any]
    ) -> None:
        """Emit a trade signal based on wallet activity for copy trading."""
        if wallet.ai_quality_score is not None and wallet.ai_quality_score < 5.0:
            logger.info(
                "Skipping copy: low wallet quality",
                address=wallet.address[:10],
                score=wallet.ai_quality_score,
            )
            return

        copy_size = float(tx.get("size", 0)) * wallet.copy_size_multiplier

        await event_bus.publish(
            Events.TRADE_SIGNAL,
            signal={
                "market_id": "",
                "condition_id": tx.get("condition_id", ""),
                "token_id": tx.get("token_id", ""),
                "outcome": tx.get("outcome", ""),
                "side": tx.get("side", "buy"),
                "price": float(tx.get("price", 0)),
                "size": copy_size,
                "strategy": f"copy_{wallet.address[:8]}",
                "source": "wallet_copy",
                "source_wallet": wallet.address,
            },
        )

    async def _gather_wallet_stats(
        self, session: AsyncSession, address: str
    ) -> dict[str, Any]:
        result = await session.execute(
            select(WalletTransaction).where(
                WalletTransaction.wallet_address == address
            ).order_by(WalletTransaction.created_at.desc()).limit(100)
        )
        transactions = result.scalars().all()

        if not transactions:
            return {
                "address": address,
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_size": 0,
                "avg_hold_hours": 0,
                "unique_markets": 0,
                "recent_trades": [],
            }

        total = len(transactions)
        sizes = [t.size * t.price for t in transactions]
        unique_markets = len(set(t.condition_id for t in transactions))

        recent = [
            {
                "side": t.side,
                "outcome": t.outcome or "",
                "price": t.price,
                "size": t.size * t.price,
                "market": t.condition_id[:30],
            }
            for t in transactions[:20]
        ]

        return {
            "address": address,
            "total_trades": total,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_size": sum(sizes) / len(sizes) if sizes else 0,
            "avg_hold_hours": 0,
            "unique_markets": unique_markets,
            "recent_trades": recent,
        }

    async def get_all_wallets(self) -> list[dict[str, Any]]:
        async with get_session() as session:
            result = await session.execute(
                select(WatchedWallet).where(WatchedWallet.is_active == True)
            )
            wallets = result.scalars().all()
            return [
                {
                    "address": w.address,
                    "label": w.label,
                    "copy_enabled": w.copy_enabled,
                    "copy_size_multiplier": w.copy_size_multiplier,
                    "total_trades": w.total_trades,
                    "win_rate": w.win_rate,
                    "ai_quality_score": w.ai_quality_score,
                    "ai_strategy_class": w.ai_strategy_class,
                    "ai_confidence": w.ai_confidence,
                    "ai_analyzed_at": str(w.ai_analyzed_at) if w.ai_analyzed_at else None,
                }
                for w in wallets
            ]
