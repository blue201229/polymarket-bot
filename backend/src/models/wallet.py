"""Wallet model — tracked wallets for analysis and copy trading."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from .base import TimestampMixin, UUIDMixin


class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"

    address: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Tracking config
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    copy_trade_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    copy_trade_max_size_usdc: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    copy_trade_size_pct: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)

    # Performance stats (computed from trade history)
    total_trades: Mapped[int] = mapped_column(nullable=False, default=0)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_volume_usdc: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_pnl_usdc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # AI wallet analysis (Phase 3)
    ai_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-10
    ai_strategy_class: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # scalper/arb/momentum
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Last activity
    last_trade_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Wallet {self.address[:10]}... score={self.ai_quality_score}>"


class WalletTrade(Base, UUIDMixin, TimestampMixin):
    """Raw trade events observed from a tracked wallet."""

    __tablename__ = "wallet_trades"

    wallet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    condition_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
