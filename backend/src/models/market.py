from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.models.base import Base


class MarketStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"
    PAUSED = "paused"


class Market(Base):
    __tablename__ = "markets"

    condition_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=MarketStatus.ACTIVE)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    volume: Mapped[float] = mapped_column(Float, default=0.0)
    volume_24h: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # AI-generated fields
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_scored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    slug: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    outcomes: Mapped[list[MarketOutcome]] = relationship(
        "MarketOutcome", back_populates="market", cascade="all, delete-orphan"
    )


class MarketOutcome(Base):
    __tablename__ = "market_outcomes"

    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("markets.id"), index=True)
    token_id: Mapped[str] = mapped_column(String(128), index=True)
    outcome: Mapped[str] = mapped_column(String(64))
    price: Mapped[float] = mapped_column(Float, default=0.0)
    previous_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    market: Mapped[Market] = relationship("Market", back_populates="outcomes")
