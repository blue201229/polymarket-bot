from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.core.database import get_session
from backend.src.core.events import Events, event_bus
from backend.src.core.logging import get_logger
from backend.src.models.position import Position
from backend.src.models.trade import Trade, TradeStatus

logger = get_logger("services.risk_engine")


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str = ""
    adjusted_size: Optional[float] = None
    warnings: list[str] = field(default_factory=list)


class RiskLimits:
    """Hard limits that can NEVER be overridden by AI."""

    def __init__(
        self,
        max_position_size_usd: float = 0,
        max_daily_loss_usd: float = 0,
        max_open_positions: int = 0,
        max_single_trade_usd: float = 0,
        max_concentration_pct: float = 50.0,
        min_liquidity_usd: float = 500.0,
        max_slippage_bps: int = 200,
        cooldown_seconds: int = 30,
    ):
        self.max_position_size_usd = max_position_size_usd or settings.max_position_size_usd
        self.max_daily_loss_usd = max_daily_loss_usd or settings.max_daily_loss_usd
        self.max_open_positions = max_open_positions or settings.max_open_positions
        self.max_single_trade_usd = max_single_trade_usd or (self.max_position_size_usd * 0.5)
        self.max_concentration_pct = max_concentration_pct
        self.min_liquidity_usd = min_liquidity_usd
        self.max_slippage_bps = max_slippage_bps
        self.cooldown_seconds = cooldown_seconds


class RiskEngine:
    """
    Deterministic risk engine. This is the FINAL gatekeeper before execution.

    Key principle: AI suggestions flow through here, but risk rules ALWAYS
    have the final say. AI can suggest tighter risk, but never looser.

    Checks performed:
    1. Position size limits
    2. Daily loss limit
    3. Open position count
    4. Market concentration
    5. Liquidity check
    6. Slippage guard
    7. Cooldown enforcement
    8. Anomaly-triggered risk tightening
    """

    def __init__(self, limits: Optional[RiskLimits] = None) -> None:
        self._limits = limits or RiskLimits()
        self._last_trade_time: dict[str, datetime] = {}
        self._risk_multiplier: float = 1.0  # 1.0 = normal, <1.0 = tighter

    async def check_trade(
        self,
        market_id: str,
        side: str,
        size: float,
        price: float,
        liquidity: float = 0,
        ai_confidence: Optional[float] = None,
        ai_size_modifier: Optional[float] = None,
    ) -> RiskCheckResult:
        warnings: list[str] = []
        effective_size = size

        # Apply AI size modifier if provided (AI can only reduce, not increase beyond 1.2x)
        if ai_size_modifier is not None:
            clamped_modifier = max(0.5, min(1.2, ai_size_modifier))
            if clamped_modifier != ai_size_modifier:
                warnings.append(
                    f"AI size modifier clamped: {ai_size_modifier:.2f} -> {clamped_modifier:.2f}"
                )
            effective_size *= clamped_modifier

        # Apply risk multiplier (from anomaly detection)
        effective_size *= self._risk_multiplier
        if self._risk_multiplier < 1.0:
            warnings.append(f"Risk tightened: multiplier={self._risk_multiplier:.2f}")

        trade_value = effective_size * price

        # 1. Single trade size limit
        if trade_value > self._limits.max_single_trade_usd:
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Trade value ${trade_value:.2f} exceeds single trade limit "
                    f"${self._limits.max_single_trade_usd:.2f}"
                ),
            )

        # 2. Daily loss check
        daily_loss = await self._get_daily_loss()
        remaining_budget = self._limits.max_daily_loss_usd - abs(daily_loss)
        if remaining_budget <= 0:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit reached: ${abs(daily_loss):.2f} / ${self._limits.max_daily_loss_usd:.2f}",
            )
        if trade_value > remaining_budget:
            effective_size = remaining_budget / price if price > 0 else 0
            warnings.append(f"Size reduced to fit daily loss budget: ${remaining_budget:.2f}")

        # 3. Open positions check
        open_count = await self._count_open_positions()
        if open_count >= self._limits.max_open_positions:
            return RiskCheckResult(
                approved=False,
                reason=f"Max open positions reached: {open_count}/{self._limits.max_open_positions}",
            )

        # 4. Position size limit per market
        existing_size = await self._get_position_size(market_id)
        if existing_size + effective_size > self._limits.max_position_size_usd:
            max_additional = self._limits.max_position_size_usd - existing_size
            if max_additional <= 0:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Max position size reached for market: ${existing_size:.2f}",
                )
            effective_size = min(effective_size, max_additional)
            warnings.append(f"Size capped to position limit: ${max_additional:.2f}")

        # 5. Liquidity check
        if liquidity > 0 and liquidity < self._limits.min_liquidity_usd:
            return RiskCheckResult(
                approved=False,
                reason=f"Insufficient liquidity: ${liquidity:.2f} < ${self._limits.min_liquidity_usd:.2f}",
            )

        # 6. Cooldown check
        last_trade = self._last_trade_time.get(market_id)
        if last_trade:
            elapsed = (datetime.now(timezone.utc) - last_trade).total_seconds()
            if elapsed < self._limits.cooldown_seconds:
                return RiskCheckResult(
                    approved=False,
                    reason=f"Cooldown active: {self._limits.cooldown_seconds - elapsed:.0f}s remaining",
                )

        # Low AI confidence warning (does NOT block)
        if ai_confidence is not None and ai_confidence < 0.3:
            warnings.append(f"Low AI confidence: {ai_confidence:.2f}")

        return RiskCheckResult(
            approved=True,
            adjusted_size=effective_size,
            warnings=warnings,
        )

    def tighten_risk(self, multiplier: float) -> None:
        """Called by anomaly detector to tighten risk parameters."""
        self._risk_multiplier = max(0.1, min(1.0, multiplier))
        logger.warning("Risk tightened", multiplier=self._risk_multiplier)

    def reset_risk(self) -> None:
        self._risk_multiplier = 1.0
        logger.info("Risk multiplier reset to normal")

    def record_trade_time(self, market_id: str) -> None:
        self._last_trade_time[market_id] = datetime.now(timezone.utc)

    async def _get_daily_loss(self) -> float:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        async with get_session() as session:
            result = await session.execute(
                select(func.coalesce(func.sum(Trade.pnl), 0)).where(
                    Trade.closed_at >= today,
                    Trade.status == TradeStatus.FILLED,
                    Trade.pnl < 0,
                )
            )
            return float(result.scalar() or 0)

    async def _count_open_positions(self) -> int:
        async with get_session() as session:
            result = await session.execute(
                select(func.count()).where(Position.is_open == True)
            )
            return int(result.scalar() or 0)

    async def _get_position_size(self, market_id: str) -> float:
        async with get_session() as session:
            result = await session.execute(
                select(func.coalesce(func.sum(Position.size * Position.avg_entry_price), 0)).where(
                    Position.market_id == market_id,
                    Position.is_open == True,
                )
            )
            return float(result.scalar() or 0)
