"""Signal model — raw trading signals from strategy engines."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from .base import TimestampMixin, UUIDMixin


class Signal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "signals"

    # Signal origin
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    condition_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    market_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Signal details
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_size_usdc: Mapped[float] = mapped_column(Float, nullable=False)

    # Deterministic signal quality
    spread_at_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity_at_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Signal outcome
    acted_on: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trade_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI filter result (advisory layer — always recorded)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_size_modifier: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_decision: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Historical backtest result (filled later)
    outcome_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    actual_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<Signal {self.strategy} {self.side} {self.condition_id[:8]}>"
