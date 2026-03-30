from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StrategySignal:
    market_id: str
    condition_id: str
    token_id: str
    outcome: str
    side: str
    price: float
    size: float
    strategy: str
    confidence: float = 0.5
    context: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    Strategies produce signals; they do NOT execute trades.
    The execution pipeline handles AI filtering and risk checking.
    """

    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name = name
        self.enabled = enabled

    @abstractmethod
    async def evaluate(self, market_data: dict[str, Any]) -> Optional[StrategySignal]:
        """
        Evaluate a market and optionally return a trade signal.
        Returns None if no signal is generated.
        """
        ...

    @abstractmethod
    async def should_close(
        self, position: dict[str, Any], market_data: dict[str, Any]
    ) -> Optional[StrategySignal]:
        """
        Check if an existing position should be closed.
        Returns a sell signal if yes, None otherwise.
        """
        ...
