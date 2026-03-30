from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.src.ai.ai_engine import AIEngine, ai_engine
from backend.src.core.logging import get_logger

logger = get_logger("ai.scoring")

PROMPT_PATH = Path(__file__).parent / "prompts" / "market_prompt.txt"


@dataclass
class MarketScore:
    score: float = 0.0
    narrative_strength: float = 0.0
    resolution_clarity: float = 0.0
    volatility_potential: float = 0.0
    inefficiency_likelihood: float = 0.0
    reasoning: str = ""
    tags: list[str] = field(default_factory=list)
    suggested_action: str = "skip"
    cached: bool = False
    latency_ms: int = 0


class MarketScorer:
    """
    AI-assisted market scoring.

    Evaluates markets that have passed hard filters (volume, liquidity, status)
    and assigns a quality score used for prioritization.

    This is ADVISORY only - deterministic filters always run first.
    """

    def __init__(self, engine: Optional[AIEngine] = None) -> None:
        self._engine = engine or ai_engine
        self._prompt_template = PROMPT_PATH.read_text()

    def _build_prompt(self, market_data: dict[str, Any]) -> str:
        outcomes_str = ", ".join(
            f"{o.get('outcome', '?')}: {o.get('price', 0):.3f}"
            for o in market_data.get("outcomes", [])
        )
        return self._prompt_template.format(
            question=market_data.get("question", ""),
            description=market_data.get("description", "N/A"),
            category=market_data.get("category", "Unknown"),
            end_date=market_data.get("end_date", "N/A"),
            volume=market_data.get("volume", 0),
            volume_24h=market_data.get("volume_24h", 0),
            liquidity=market_data.get("liquidity", 0),
            spread=market_data.get("spread", "N/A"),
            outcomes=outcomes_str,
        )

    async def score_market(self, market_data: dict[str, Any]) -> MarketScore:
        prompt = self._build_prompt(market_data)

        response = await self._engine.complete(
            prompt=prompt,
            system="You are a prediction market analyst. Return only valid JSON.",
            temperature=0.2,
            max_tokens=512,
        )

        if response is None:
            logger.warning("AI scoring unavailable, returning default", 
                         market=market_data.get("question", "")[:60])
            return MarketScore(reasoning="AI unavailable - using default score")

        try:
            data = response.parse_json()
            return MarketScore(
                score=float(data.get("score", 0)),
                narrative_strength=float(data.get("narrative_strength", 0)),
                resolution_clarity=float(data.get("resolution_clarity", 0)),
                volatility_potential=float(data.get("volatility_potential", 0)),
                inefficiency_likelihood=float(data.get("inefficiency_likelihood", 0)),
                reasoning=data.get("reasoning", ""),
                tags=data.get("tags", []),
                suggested_action=data.get("suggested_action", "skip"),
                cached=response.cached,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.error("Failed to parse AI score response", error=str(e))
            return MarketScore(reasoning=f"Parse error: {e}")

    async def score_markets_batch(
        self, markets: list[dict[str, Any]]
    ) -> list[MarketScore]:
        """Score multiple markets concurrently."""
        requests = [
            {
                "prompt": self._build_prompt(m),
                "system": "You are a prediction market analyst. Return only valid JSON.",
                "temperature": 0.2,
                "max_tokens": 512,
            }
            for m in markets
        ]

        responses = await self._engine.batch_complete(requests)
        results = []

        for i, response in enumerate(responses):
            if response is None:
                results.append(MarketScore(reasoning="AI unavailable"))
                continue
            try:
                data = response.parse_json()
                results.append(MarketScore(
                    score=float(data.get("score", 0)),
                    narrative_strength=float(data.get("narrative_strength", 0)),
                    resolution_clarity=float(data.get("resolution_clarity", 0)),
                    volatility_potential=float(data.get("volatility_potential", 0)),
                    inefficiency_likelihood=float(data.get("inefficiency_likelihood", 0)),
                    reasoning=data.get("reasoning", ""),
                    tags=data.get("tags", []),
                    suggested_action=data.get("suggested_action", "skip"),
                    cached=response.cached,
                    latency_ms=response.latency_ms,
                ))
            except Exception as e:
                logger.error("Failed to parse batch score", index=i, error=str(e))
                results.append(MarketScore(reasoning=f"Parse error: {e}"))

        return results
