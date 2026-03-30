from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.models.base import Base


class TradeStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PAPER = "paper"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Trade(Base):
    __tablename__ = "trades"

    market_id: Mapped[str] = mapped_column(String(36), index=True)
    condition_id: Mapped[str] = mapped_column(String(128), index=True)
    token_id: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(64))

    side: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), default=TradeStatus.PENDING)
    order_type: Mapped[str] = mapped_column(String(16), default="limit")

    price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    filled_size: Mapped[float] = mapped_column(Float, default=0.0)
    filled_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    strategy: Mapped[str] = mapped_column(String(64), index=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)

    # AI-assisted fields
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_size_modifier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_skip_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Execution details
    order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    slippage_bps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee: Mapped[float] = mapped_column(Float, default=0.0)

    # PnL
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
