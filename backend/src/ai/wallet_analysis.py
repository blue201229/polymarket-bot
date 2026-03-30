from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.wallet_analysis")

PROMPT_PATH = Path(__file__).parent / "prompts" / "wallet_prompt.txt"


@dataclass
class WalletProfile:
    quality_score: float = 0.0
    strategy_classification: str = "unknown"
    confidence: float = 0.0
    risk_profile: str = "unknown"
    timing_pattern: str = "unknown"
    consistency_score: float = 0.0
    copy_recommendation: str = "avoid"
    reasoning: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    cached: bool = False
    latency_ms: int = 0


class WalletAnalyzer:
    """
    AI-assisted wallet behavior analysis.

    Analyzes watched wallets' trading patterns to determine quality,
    strategy type, and suitability for copy trading.

    Inputs are deterministic wallet statistics; AI provides classification.
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine
        self._prompt_template = PROMPT_PATH.read_text()

    def _build_prompt(self, wallet_data: dict[str, Any]) -> str:
        recent_trades_str = "\n".join(
            f"  - {t.get('side', '?')} {t.get('outcome', '?')} @ {t.get('price', 0):.3f}, "
            f"size: ${t.get('size', 0):,.2f}, market: {t.get('market', '?')[:50]}"
            for t in wallet_data.get("recent_trades", [])[:20]
        )
        return self._prompt_template.format(
            address=wallet_data.get("address", ""),
            total_trades=wallet_data.get("total_trades", 0),
            win_rate=wallet_data.get("win_rate", 0),
            total_pnl=wallet_data.get("total_pnl", 0),
            avg_size=wallet_data.get("avg_size", 0),
            avg_hold_hours=wallet_data.get("avg_hold_hours", 0),
            unique_markets=wallet_data.get("unique_markets", 0),
            recent_trades=recent_trades_str or "  No recent trades available",
        )

    async def analyze_wallet(self, wallet_data: dict[str, Any]) -> WalletProfile:
        prompt = self._build_prompt(wallet_data)

        response = await self._engine.complete(
            prompt=prompt,
            system="You are a blockchain trading analyst. Return only valid JSON.",
            temperature=0.3,
            max_tokens=512,
        )

        if response is None:
            logger.warning("AI wallet analysis unavailable",
                         address=wallet_data.get("address", "")[:10])
            return WalletProfile(reasoning="AI unavailable")

        try:
            data = response.parse_json()
            return WalletProfile(
                quality_score=float(data.get("quality_score", 0)),
                strategy_classification=data.get("strategy_classification", "unknown"),
                confidence=float(data.get("confidence", 0)),
                risk_profile=data.get("risk_profile", "unknown"),
                timing_pattern=data.get("timing_pattern", "unknown"),
                consistency_score=float(data.get("consistency_score", 0)),
                copy_recommendation=data.get("copy_recommendation", "avoid"),
                reasoning=data.get("reasoning", ""),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse wallet analysis", error=str(e))
            return WalletProfile(reasoning=f"Parse error: {e}")
