"""Market model — represents a Polymarket prediction market."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from .base import TimestampMixin, UUIDMixin


class Market(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "markets"

    # Polymarket identifiers
    condition_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    question_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    slug: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Market metadata
    question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array string

    # Resolution
    resolution_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # YES/NO/N/A

    # Pricing (YES token)
    best_bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_ask: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mid_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Volume & liquidity
    volume_24h: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    volume_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    open_interest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepting_orders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI scoring fields (populated by AI module asynchronously)
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    ai_scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Computed quality flags (deterministic)
    liquidity_tier: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # high/med/low
    spread_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<Market {self.condition_id[:8]} q={self.question[:40]}>"
