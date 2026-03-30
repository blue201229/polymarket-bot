from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.optimizer")

OPTIMIZER_SYSTEM = """You are a quantitative trading parameter optimizer for prediction markets.
Analyze recent performance data and suggest parameter adjustments.
Be conservative — small incremental changes are preferred over large shifts.
Return only valid JSON."""

OPTIMIZER_PROMPT = """Analyze the following trading performance and suggest parameter adjustments.

Current Parameters:
- Slippage Limit: {slippage_bps} bps
- Entry Threshold: {entry_threshold}
- Max Position Size: ${max_position_size}
- Cooldown Between Trades: {cooldown_seconds}s
- Min Liquidity: ${min_liquidity}
- Min Volume 24h: ${min_volume_24h}

Recent Performance (last {window_days} days):
- Total Trades: {total_trades}
- Win Rate: {win_rate}%
- Net PnL: ${net_pnl:,.2f}
- Avg Trade PnL: ${avg_pnl:,.2f}
- Max Drawdown: ${max_drawdown:,.2f}
- Avg Slippage: {avg_slippage} bps
- Trades Skipped (liquidity): {skipped_liquidity}
- Trades Skipped (spread): {skipped_spread}

Market Conditions:
- Avg Market Volume: ${avg_market_volume:,.0f}
- Avg Spread: {avg_spread} bps
- Active Markets: {active_markets}

Return ONLY a JSON object:
{{
  "suggestions": [
    {{
      "parameter": "<parameter_name>",
      "current_value": <current>,
      "suggested_value": <new>,
      "change_percent": <float>,
      "reasoning": "<why this change>"
    }}
  ],
  "overall_assessment": "<brief assessment>",
  "confidence": <float 0-1>,
  "risk_level": "<low|medium|high>"
}}"""


@dataclass
class ParameterSuggestion:
    parameter: str
    current_value: float
    suggested_value: float
    change_percent: float
    reasoning: str


@dataclass
class OptimizationResult:
    suggestions: list[ParameterSuggestion] = field(default_factory=list)
    overall_assessment: str = ""
    confidence: float = 0.0
    risk_level: str = "low"
    cached: bool = False
    latency_ms: int = 0


class ParameterOptimizer:
    """
    AI-assisted parameter tuning.

    Analyzes recent performance and market conditions to suggest
    parameter adjustments. Suggestions are NEVER auto-applied —
    they must be reviewed and approved through the UI.
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine

    async def optimize(self, performance_data: dict[str, Any]) -> OptimizationResult:
        prompt = OPTIMIZER_PROMPT.format(
            slippage_bps=performance_data.get("slippage_bps", 50),
            entry_threshold=performance_data.get("entry_threshold", 0.6),
            max_position_size=performance_data.get("max_position_size", 100),
            cooldown_seconds=performance_data.get("cooldown_seconds", 60),
            min_liquidity=performance_data.get("min_liquidity", 1000),
            min_volume_24h=performance_data.get("min_volume_24h", 5000),
            window_days=performance_data.get("window_days", 7),
            total_trades=performance_data.get("total_trades", 0),
            win_rate=performance_data.get("win_rate", 0),
            net_pnl=performance_data.get("net_pnl", 0),
            avg_pnl=performance_data.get("avg_pnl", 0),
            max_drawdown=performance_data.get("max_drawdown", 0),
            avg_slippage=performance_data.get("avg_slippage", 0),
            skipped_liquidity=performance_data.get("skipped_liquidity", 0),
            skipped_spread=performance_data.get("skipped_spread", 0),
            avg_market_volume=performance_data.get("avg_market_volume", 0),
            avg_spread=performance_data.get("avg_spread", 0),
            active_markets=performance_data.get("active_markets", 0),
        )

        response = await self._engine.complete(
            prompt=prompt,
            system=OPTIMIZER_SYSTEM,
            temperature=0.3,
            max_tokens=1024,
        )

        if response is None:
            logger.warning("AI optimizer unavailable")
            return OptimizationResult(overall_assessment="AI unavailable")

        try:
            data = response.parse_json()
            suggestions = [
                ParameterSuggestion(
                    parameter=s.get("parameter", ""),
                    current_value=float(s.get("current_value", 0)),
                    suggested_value=float(s.get("suggested_value", 0)),
                    change_percent=float(s.get("change_percent", 0)),
                    reasoning=s.get("reasoning", ""),
                )
                for s in data.get("suggestions", [])
            ]
            return OptimizationResult(
                suggestions=suggestions,
                overall_assessment=data.get("overall_assessment", ""),
                confidence=float(data.get("confidence", 0)),
                risk_level=data.get("risk_level", "low"),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse optimization result", error=str(e))
            return OptimizationResult(overall_assessment=f"Parse error: {e}")
