from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.models.base import Base


class WatchedWallet(Base):
    __tablename__ = "watched_wallets"

    address: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    copy_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    copy_size_multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    total_trades: Mapped[int] = mapped_column(default=0)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # AI-generated analysis
    ai_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_strategy_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    wallet_address: Mapped[str] = mapped_column(String(64), index=True)
    condition_id: Mapped[str] = mapped_column(String(128))
    token_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    side: Mapped[str] = mapped_column(String(8))
    size: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
