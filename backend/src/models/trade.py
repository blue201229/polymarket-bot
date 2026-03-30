"""Trade model — records all trade decisions and executions."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from .base import TimestampMixin, UUIDMixin


class TradeStatus(str, Enum):
    PENDING = "pending"
    RISK_REJECTED = "risk_rejected"      # Hard stop by risk engine — never bypassed by AI
    AI_SKIPPED = "ai_skipped"            # AI suggested skip (optional layer)
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeSource(str, Enum):
    MANUAL = "manual"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    COPY_TRADE = "copy_trade"
    MEAN_REVERSION = "mean_reversion"
    CRYPTO_BOT = "crypto_bot"


class Trade(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trades"

    # Market reference
    market_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    condition_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Trade details
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # TradeSide
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)  # YES/NO
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # TradeSource
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TradeStatus.PENDING)

    # Sizing
    size_usdc: Mapped[float] = mapped_column(Float, nullable=False)
    size_shares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Prices
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    executed_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slippage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_slippage_pct: Mapped[float] = mapped_column(Float, default=0.02, nullable=False)

    # Paper trading flag
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Execution
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # PnL tracking
    pnl_usdc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Risk engine record (deterministic — always logged)
    risk_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    risk_rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI layer record (advisory — always logged, never forces execution)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_size_modifier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_decision: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # execute/skip
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Copy trade reference
    copied_wallet: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Trade {self.id[:8]} {self.side} {self.size_usdc}USDC @ {self.target_price} [{self.status}]>"
