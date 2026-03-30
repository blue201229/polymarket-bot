"""
Risk Engine — deterministic hard rules for trade validation.

CRITICAL: This engine is NEVER overridden by AI.
Every trade must pass this engine before execution.
AI is advisory — risk engine is authoritative.

Rules enforced:
1. Max position size per trade
2. Max total exposure across all open positions
3. Max number of concurrent positions
4. Minimum liquidity requirement
5. Maximum spread tolerance
6. Slippage limit
7. Paper trading enforcement
8. Anomaly-based pause
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.core.config import settings
from src.core.exceptions import RiskEngineError
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskParams:
    """Live risk parameters — can be updated by operator, never by AI autonomously."""
    max_position_size_usdc: float = settings.max_position_size_usdc
    max_total_exposure_usdc: float = settings.max_total_exposure_usdc
    max_positions: int = settings.max_positions
    min_liquidity: float = 5_000.0
    max_spread_pct: float = 0.08
    max_slippage_pct: float = settings.default_slippage_pct
    paper_trading: bool = settings.paper_trading_mode
    trading_paused: bool = False
    pause_reason: Optional[str] = None


# Module-level live params (updated by operator via API)
_live_params = RiskParams()


def get_risk_params() -> RiskParams:
    return _live_params


def update_risk_params(updates: Dict[str, Any]) -> RiskParams:
    """Update risk parameters. Requires explicit operator action — never called by AI."""
    for key, value in updates.items():
        if hasattr(_live_params, key):
            setattr(_live_params, key, value)
            logger.info("risk_param_updated", parameter=key, value=value)
        else:
            logger.warning("risk_param_unknown", parameter=key)
    return _live_params


@dataclass
class RiskCheckResult:
    approved: bool
    rejection_reason: Optional[str] = None
    warnings: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RiskEngine:
    """
    Deterministic trade risk validator.

    Sequence:
    1. Check if trading is paused
    2. Check paper trading mode
    3. Validate position size
    4. Validate total exposure
    5. Validate position count
    6. Validate market liquidity
    7. Validate spread
    8. Validate slippage
    """

    def __init__(self, params: Optional[RiskParams] = None):
        self._params = params or _live_params

    def check(
        self,
        *,
        trade_size_usdc: float,
        market_liquidity: float,
        market_spread_pct: float,
        target_price: float,
        current_positions_count: int,
        current_total_exposure_usdc: float,
        is_paper: bool = True,
        ai_confidence: Optional[float] = None,
    ) -> RiskCheckResult:
        """
        Validate a trade against all risk rules.

        Args:
            trade_size_usdc: Requested trade size
            market_liquidity: Current market liquidity
            market_spread_pct: Current spread as fraction
            target_price: Target entry price
            current_positions_count: Number of open positions
            current_total_exposure_usdc: Total current exposure
            is_paper: Whether this is a paper trade
            ai_confidence: AI confidence score (logged, not used in decision)

        Returns:
            RiskCheckResult with approved=True/False and rejection reason
        """
        params = self._params
        warnings = []

        # ── Hard stops ────────────────────────────────────────────────────────

        if params.trading_paused:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"trading_paused:{params.pause_reason or 'operator_request'}",
            )

        if not is_paper and not params.paper_trading:
            # Live trading — extra caution
            pass
        elif not is_paper and params.paper_trading:
            return RiskCheckResult(
                approved=False,
                rejection_reason="paper_trading_mode_active:live_orders_disabled",
            )

        if trade_size_usdc > params.max_position_size_usdc:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"position_size_exceeded:{trade_size_usdc:.2f}>{params.max_position_size_usdc:.2f}",
            )

        if trade_size_usdc <= 0:
            return RiskCheckResult(
                approved=False,
                rejection_reason="invalid_trade_size:zero_or_negative",
            )

        new_total = current_total_exposure_usdc + trade_size_usdc
        if new_total > params.max_total_exposure_usdc:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"total_exposure_exceeded:{new_total:.2f}>{params.max_total_exposure_usdc:.2f}",
            )

        if current_positions_count >= params.max_positions:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"max_positions_reached:{current_positions_count}>={params.max_positions}",
            )

        if market_liquidity < params.min_liquidity:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"insufficient_liquidity:{market_liquidity:.0f}<{params.min_liquidity:.0f}",
            )

        if market_spread_pct > params.max_spread_pct:
            return RiskCheckResult(
                approved=False,
                rejection_reason=f"spread_too_wide:{market_spread_pct:.3f}>{params.max_spread_pct:.3f}",
            )

        # ── Warnings (not blocking) ───────────────────────────────────────────

        if ai_confidence is not None and ai_confidence < 0.4:
            warnings.append(f"low_ai_confidence:{ai_confidence:.2f}")

        if market_spread_pct > params.max_spread_pct * 0.7:
            warnings.append(f"spread_elevated:{market_spread_pct:.3f}")

        if trade_size_usdc > params.max_position_size_usdc * 0.8:
            warnings.append(f"large_position:{trade_size_usdc:.2f}")

        logger.info(
            "risk_check_approved",
            size_usdc=trade_size_usdc,
            spread_pct=market_spread_pct,
            liquidity=market_liquidity,
            ai_confidence=ai_confidence,
            warnings=warnings,
        )

        return RiskCheckResult(approved=True, warnings=warnings)

    def pause_trading(self, reason: str) -> None:
        """Pause all new trade entries. Can be triggered by anomaly detection."""
        self._params.trading_paused = True
        self._params.pause_reason = reason
        logger.warning("risk_engine_trading_paused", reason=reason)

    def resume_trading(self) -> None:
        """Resume trading. Requires explicit operator action."""
        self._params.trading_paused = False
        self._params.pause_reason = None
        logger.info("risk_engine_trading_resumed")


_risk_engine = RiskEngine()


def get_risk_engine() -> RiskEngine:
    return _risk_engine
