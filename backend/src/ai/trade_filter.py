from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.trade_filter")

PROMPT_PATH = Path(__file__).parent / "prompts" / "trade_prompt.txt"


@dataclass
class TradeEvaluation:
    confidence: float = 0.0
    size_modifier: float = 1.0
    recommendation: str = "skip"
    reasoning: str = ""
    risk_flags: list[str] = field(default_factory=list)
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    cached: bool = False
    latency_ms: int = 0


class TradeFilter:
    """
    AI-assisted trade signal filtering.

    Evaluates candidate trades AFTER strategy generates a signal but BEFORE
    the risk engine makes the final decision. AI provides confidence and
    sizing suggestions; deterministic risk rules still have final say.

    Pipeline: Strategy Signal -> AI Filter -> Risk Engine -> Execution
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine
        self._prompt_template = PROMPT_PATH.read_text()

    def _build_prompt(self, signal: dict[str, Any]) -> str:
        price_history_str = "\n".join(
            f"  {p.get('timestamp', '?')}: {p.get('price', 0):.3f}"
            for p in signal.get("price_history", [])[-10:]
        )
        return self._prompt_template.format(
            strategy=signal.get("strategy", "unknown"),
            market_question=signal.get("market_question", ""),
            side=signal.get("side", ""),
            outcome=signal.get("outcome", ""),
            price=signal.get("price", 0),
            size=signal.get("size", 0),
            best_bid=signal.get("best_bid", 0),
            best_ask=signal.get("best_ask", 0),
            spread_bps=signal.get("spread_bps", 0),
            volume_24h=signal.get("volume_24h", 0),
            liquidity=signal.get("liquidity", 0),
            time_to_expiry=signal.get("time_to_expiry", "unknown"),
            price_history=price_history_str or "  No history available",
            strategy_win_rate=signal.get("strategy_win_rate", 0),
            strategy_avg_pnl=signal.get("strategy_avg_pnl", 0),
            strategy_total_trades=signal.get("strategy_total_trades", 0),
        )

    async def evaluate_trade(self, signal: dict[str, Any]) -> TradeEvaluation:
        prompt = self._build_prompt(signal)

        response = await self._engine.complete(
            prompt=prompt,
            system=(
                "You are a risk-aware trading assistant. Provide honest, conservative "
                "assessments. Return only valid JSON."
            ),
            temperature=0.2,
            max_tokens=512,
        )

        if response is None:
            logger.warning("AI trade filter unavailable, defaulting to neutral")
            return TradeEvaluation(
                confidence=0.5,
                size_modifier=1.0,
                recommendation="execute",
                reasoning="AI unavailable - passing through with neutral confidence",
            )

        try:
            data = response.parse_json()
            return TradeEvaluation(
                confidence=float(data.get("confidence", 0.5)),
                size_modifier=max(0.5, min(1.5, float(data.get("size_modifier", 1.0)))),
                recommendation=data.get("recommendation", "skip"),
                reasoning=data.get("reasoning", ""),
                risk_flags=data.get("risk_flags", []),
                suggested_stop_loss=data.get("suggested_stop_loss"),
                suggested_take_profit=data.get("suggested_take_profit"),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse trade evaluation", error=str(e))
            return TradeEvaluation(
                confidence=0.5,
                size_modifier=1.0,
                recommendation="execute",
                reasoning=f"Parse error (defaulting to neutral): {e}",
            )
