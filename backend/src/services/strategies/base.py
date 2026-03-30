"""Base class for all trading strategies."""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.models.signal import Signal

logger = get_logger(__name__)


@dataclass
class StrategyConfig:
    """Per-strategy configuration."""
    name: str
    enabled: bool = True
    min_ai_score: float = 5.0          # Minimum market AI score to consider
    min_liquidity: float = 10_000.0
    max_spread_pct: float = 0.05
    base_size_usdc: float = 20.0
    entry_threshold: float = 0.03       # Minimum price edge
    cooldown_seconds: int = 300
    use_ai_filter: bool = True          # Apply AI trade filter
    ai_min_confidence: float = 0.5     # Skip if AI confidence below this
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategySignal:
    """Output of a strategy's analysis."""
    strategy: str
    condition_id: str
    side: str          # buy/sell
    outcome: str       # Yes/No
    target_price: float
    suggested_size_usdc: float
    confidence: float  # Strategy's own confidence (0-1, deterministic)
    reasoning: str
    market_data: Dict[str, Any]


class BaseStrategy(ABC):
    """
    All trading strategies inherit from this.

    Responsibilities:
    - Analyze market data
    - Emit signals
    - Track cooldowns
    """

    def __init__(self, config: StrategyConfig):
        self.config = config
        self._cooldowns: Dict[str, datetime] = {}
        self._trade_count = 0
        self._win_count = 0
        self._logger = get_logger(f"strategy.{config.name}")

    @abstractmethod
    async def analyze(self, market: Dict[str, Any]) -> Optional[StrategySignal]:
        """Analyze a market and return a signal, or None if no opportunity."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    def win_rate(self) -> float:
        if self._trade_count == 0:
            return 0.5
        return self._win_count / self._trade_count

    def is_on_cooldown(self, condition_id: str) -> bool:
        last = self._cooldowns.get(condition_id)
        if not last:
            return False
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed < self.config.cooldown_seconds

    def set_cooldown(self, condition_id: str) -> None:
        self._cooldowns[condition_id] = datetime.now(timezone.utc)

    def record_outcome(self, won: bool) -> None:
        self._trade_count += 1
        if won:
            self._win_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "strategy": self.config.name,
            "trade_count": self._trade_count,
            "win_count": self._win_count,
            "win_rate": round(self.win_rate(), 3),
        }
