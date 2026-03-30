"""AI decision log model — every AI call is recorded for auditability."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from .base import TimestampMixin, UUIDMixin


class AILog(Base, UUIDMixin, TimestampMixin):
    """
    Every AI call (scoring, filtering, analysis) is stored here.
    This enables:
    - Auditability (no black box)
    - Performance measurement (did AI improve outcomes?)
    - Training data for future refinement
    """

    __tablename__ = "ai_logs"

    component: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)

    # Reference keys (optional, depending on context)
    market_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    trade_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    wallet_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    signal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # IO (always stored)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 for dedup
    prompt_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_parsed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Performance
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Decision impact tracking (filled in post-analysis)
    decision_impact: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    outcome_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    def __repr__(self) -> str:
        return f"<AILog {self.component} model={self.model} latency={self.latency_ms}ms>"
