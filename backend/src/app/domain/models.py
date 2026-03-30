from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class HardFilterDecision(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    deterministic_score: float = Field(ge=0, le=10)


class AIScore(BaseModel):
    source: Literal["ai", "fallback", "disabled"]
    score: float = Field(ge=0, le=10)
    reasoning: str
    tags: list[str] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    decision_impact: str = "advisory"


class MarketSnapshot(BaseModel):
    market_id: str
    question: str
    category: str
    liquidity: float = Field(ge=0)
    volume_24h: float = Field(ge=0)
    spread_bps: int = Field(ge=0)
    resolution_clarity: float = Field(ge=0, le=1)
    end_time: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketCandidate(BaseModel):
    market: MarketSnapshot
    hard_filter: HardFilterDecision
    deterministic_priority: float = Field(ge=0, le=10)
    ai_score: AIScore | None = None
    priority_score: float = Field(ge=0, le=10)


class MarketDiscoveryResponse(BaseModel):
    generated_at: datetime
    ai_enabled: bool
    comparison_mode_available: bool = True
    candidates: list[MarketCandidate]


class PhaseDefinition(BaseModel):
    name: str
    scope: list[str]
    ai_usage: list[str]


class BlueprintResponse(BaseModel):
    backend: dict[str, Any]
    frontends: list[dict[str, Any]]
    ai_principles: list[str]
    phases: list[PhaseDefinition]


class WalletAnalysisResult(BaseModel):
    wallet: str
    quality_score: float = Field(ge=0, le=10)
    strategy_classification: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class TradeFilterDecision(BaseModel):
    execute: bool
    confidence_score: float = Field(ge=0, le=10)
    size_modifier: float = Field(ge=0)
    reasoning: str


class OptimizationSuggestion(BaseModel):
    parameter: str
    current_value: str
    suggested_value: str
    rationale: str
    requires_validation: bool = True


class AnomalySignal(BaseModel):
    signal_type: str
    severity: Literal["low", "medium", "high"]
    message: str
    suggested_action: str


class PostTradeInsight(BaseModel):
    trade_id: str
    summary: str
    improvement_suggestion: str


class CapabilityDescriptor(BaseModel):
    capability: str
    status: Literal["implemented", "scaffolded"]
    deterministic_owner: str
    ai_role: str


def sample_end_time(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)
