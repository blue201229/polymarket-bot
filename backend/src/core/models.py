from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Market(BaseModel):
    market_id: str
    question: str
    category: str
    yes_price: float = Field(ge=0.0, le=1.0)
    no_price: float = Field(ge=0.0, le=1.0)
    volume_24h: float = Field(ge=0.0)
    liquidity: float = Field(ge=0.0)
    spread_bps: float = Field(ge=0.0)
    volatility_24h: float = Field(ge=0.0)
    resolves_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30)
    )
    deterministic_priority: float | None = None
    ai_score: float | None = None
    ai_reasoning: str | None = None
    ai_tags: list[str] = Field(default_factory=list)


class MarketDiscoveryResponse(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hard_filter_count: int
    markets: list[Market]


class CandidateTrade(BaseModel):
    signal_id: str
    market_id: str
    side: Literal["yes", "no"]
    desired_size: float = Field(gt=0.0)
    liquidity: float = Field(ge=0.0)


class AIStatusResponse(BaseModel):
    enabled: bool
    timeout_seconds: float
    cache_ttl_seconds: int
    max_batch_size: int


class AiScore(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    reasoning: str
    tags: list[str] = Field(default_factory=list)
    source: Literal["ai", "fallback"]


class MarketScoreResult(BaseModel):
    market_id: str
    ai_enabled: bool
    score: AiScore


class TradeFilterDecision(BaseModel):
    signal_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    size_modifier: float = Field(gt=0.0)
    action: Literal["execute", "skip", "review"]
    explanation: str
    source: Literal["ai", "fallback"]


class AIWalletRequest(BaseModel):
    wallet: str
    entry_timing_pattern: str = "unknown"
    avg_position_size: float = Field(default=0.0, ge=0.0)
    consistency_score: float = Field(default=5.0, ge=0.0, le=10.0)
    risk_taking_score: float = Field(default=5.0, ge=0.0, le=10.0)
    preferred_categories: list[str] = Field(default_factory=list)


class AIWalletResponse(BaseModel):
    wallet: str
    wallet_quality_score: float = Field(ge=0.0, le=10.0)
    strategy_classification: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    source: Literal["ai", "fallback"]


class AITradeFilterRequest(BaseModel):
    signal_id: str
    strategy_signal: str
    orderbook_depth: float = Field(ge=0.0)
    spread_bps: float = Field(ge=0.0)
    recent_volatility: float = Field(ge=0.0)
    historical_win_rate: float = Field(ge=0.0, le=1.0)
    proposed_size: float = Field(gt=0.0)


class AITradeFilterResponse(BaseModel):
    signal_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    suggested_size_modifier: float = Field(gt=0.0)
    suggested_action: Literal["execute", "skip", "review"]
    explanation: str
    source: Literal["ai", "fallback"]


class ParameterSuggestionRequest(BaseModel):
    recent_pnl: list[float] = Field(default_factory=list)
    market_condition: Literal["calm", "trending", "volatile"] = "calm"


class ParameterSuggestion(BaseModel):
    parameter: str
    current_value: float
    suggested_value: float
    rationale: str


class ParameterSuggestionResponse(BaseModel):
    requires_validation: bool = True
    suggestions: list[ParameterSuggestion]
    note: str


class AIExplanation(BaseModel):
    context: str
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class AnomalyResponse(BaseModel):
    severity: float = Field(ge=0.0, le=10.0)
    warnings: list[str] = Field(default_factory=list)
    recommendation: Literal["continue", "tighten-risk", "pause-suggested"] = "continue"
    reasoning: str
    source: Literal["ai", "fallback"]

