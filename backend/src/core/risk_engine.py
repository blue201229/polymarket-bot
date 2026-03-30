from dataclasses import dataclass

from core.models import CandidateTrade


@dataclass(slots=True)
class RiskDecision:
    approved: bool
    reason: str
    max_size: float


class DeterministicRiskEngine:
    """
    Hard-rule risk engine. AI cannot override this decision.
    """

    def __init__(self, max_single_trade_size: float = 500.0, min_liquidity: float = 1000.0):
        self.max_single_trade_size = max_single_trade_size
        self.min_liquidity = min_liquidity

    def assess(self, trade: CandidateTrade) -> RiskDecision:
        if trade.desired_size <= 0:
            return RiskDecision(False, "Size must be positive.", 0.0)
        if trade.liquidity < self.min_liquidity:
            return RiskDecision(False, "Insufficient market liquidity.", 0.0)
        if trade.desired_size > self.max_single_trade_size:
            return RiskDecision(
                True,
                "Approved with capped size.",
                self.max_single_trade_size,
            )
        return RiskDecision(True, "Approved within deterministic rules.", trade.desired_size)
