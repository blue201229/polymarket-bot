from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.post_trade")

POST_TRADE_SYSTEM = """You are a trading performance analyst for prediction markets.
Analyze completed trades to identify patterns, mistakes, and improvement opportunities.
Be specific and actionable. Return only valid JSON."""

POST_TRADE_PROMPT = """Analyze these recently closed trades for patterns and improvements.

Trade Summary (last {window_days} days):
- Total Trades: {total_trades}
- Wins: {wins} | Losses: {losses}
- Win Rate: {win_rate}%
- Net PnL: ${net_pnl:,.2f}
- Avg Win: ${avg_win:,.2f} | Avg Loss: ${avg_loss:,.2f}
- Best Trade: ${best_trade:,.2f} | Worst Trade: ${worst_trade:,.2f}

Trade Details:
{trade_details}

Strategy Breakdown:
{strategy_breakdown}

Questions to Answer:
1. What patterns distinguish winning vs losing trades?
2. Were there missed opportunities (signals generated but skipped)?
3. Were there execution inefficiencies (bad timing, sizing)?
4. What strategy adjustments would improve results?

Return ONLY a JSON object:
{{
  "insights": [
    {{
      "category": "<pattern|timing|sizing|strategy|execution>",
      "finding": "<what was found>",
      "impact": "<how it affected results>",
      "suggestion": "<what to do differently>"
    }}
  ],
  "top_improvement": "<single most impactful change>",
  "strategy_grades": {{
    "<strategy_name>": {{
      "grade": "<A|B|C|D|F>",
      "note": "<brief>"
    }}
  }},
  "overall_assessment": "<2-3 sentence summary>"
}}"""


@dataclass
class TradeInsight:
    category: str
    finding: str
    impact: str
    suggestion: str


@dataclass
class PostTradeReport:
    insights: list[TradeInsight] = field(default_factory=list)
    top_improvement: str = ""
    strategy_grades: dict[str, dict[str, str]] = field(default_factory=dict)
    overall_assessment: str = ""
    cached: bool = False
    latency_ms: int = 0


class PostTradeAnalyzer:
    """
    AI-assisted post-trade analysis.

    Reviews completed trades to identify:
    - Why trades succeeded or failed
    - Missed opportunities
    - Execution inefficiencies
    - Strategy-level improvements

    Results are logged and displayed in the UI for human review.
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine

    async def analyze(self, performance_data: dict[str, Any]) -> PostTradeReport:
        trade_details = "\n".join(
            f"  - {t.get('strategy', '?')}: {t.get('side', '?')} {t.get('outcome', '?')} "
            f"@ {t.get('entry_price', 0):.3f} -> {t.get('exit_price', 0):.3f}, "
            f"PnL: ${t.get('pnl', 0):,.2f}, "
            f"Hold: {t.get('hold_hours', 0):.1f}h"
            for t in performance_data.get("trades", [])[-30:]
        )

        strategy_breakdown = "\n".join(
            f"  - {name}: {stats.get('trades', 0)} trades, "
            f"{stats.get('win_rate', 0):.0f}% WR, "
            f"${stats.get('pnl', 0):,.2f} PnL"
            for name, stats in performance_data.get("strategies", {}).items()
        )

        prompt = POST_TRADE_PROMPT.format(
            window_days=performance_data.get("window_days", 7),
            total_trades=performance_data.get("total_trades", 0),
            wins=performance_data.get("wins", 0),
            losses=performance_data.get("losses", 0),
            win_rate=performance_data.get("win_rate", 0),
            net_pnl=performance_data.get("net_pnl", 0),
            avg_win=performance_data.get("avg_win", 0),
            avg_loss=performance_data.get("avg_loss", 0),
            best_trade=performance_data.get("best_trade", 0),
            worst_trade=performance_data.get("worst_trade", 0),
            trade_details=trade_details or "  No trades in window",
            strategy_breakdown=strategy_breakdown or "  No strategy data",
        )

        response = await self._engine.complete(
            prompt=prompt,
            system=POST_TRADE_SYSTEM,
            temperature=0.3,
            max_tokens=1024,
            use_cache=False,
        )

        if response is None:
            logger.warning("AI post-trade analysis unavailable")
            return PostTradeReport(overall_assessment="AI unavailable")

        try:
            data = response.parse_json()
            insights = [
                TradeInsight(
                    category=i.get("category", ""),
                    finding=i.get("finding", ""),
                    impact=i.get("impact", ""),
                    suggestion=i.get("suggestion", ""),
                )
                for i in data.get("insights", [])
            ]
            return PostTradeReport(
                insights=insights,
                top_improvement=data.get("top_improvement", ""),
                strategy_grades=data.get("strategy_grades", {}),
                overall_assessment=data.get("overall_assessment", ""),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse post-trade analysis", error=str(e))
            return PostTradeReport(overall_assessment=f"Parse error: {e}")
