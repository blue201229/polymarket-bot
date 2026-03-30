"""Pydantic schemas for API request/response serialization."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Market Schemas ────────────────────────────────────────────────────────────

class MarketBase(BaseModel):
    condition_id: str
    question: str
    category: Optional[str] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    mid_price: Optional[float] = None
    spread_pct: Optional[float] = None
    volume_24h: float = 0.0
    liquidity: float = 0.0
    active: bool = True
    closed: bool = False
    end_date: Optional[datetime] = None


class MarketResponse(MarketBase):
    id: str
    ai_score: Optional[float] = None
    ai_reasoning: Optional[str] = None
    ai_tags: Optional[str] = None
    ai_scored_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarketListResponse(BaseModel):
    markets: List[MarketResponse]
    total: int
    page: int
    limit: int


# ── Trade Schemas ─────────────────────────────────────────────────────────────

class TradeResponse(BaseModel):
    id: str
    condition_id: str
    side: str
    outcome: str
    source: str
    status: str
    size_usdc: float
    target_price: float
    executed_price: Optional[float] = None
    slippage_pct: Optional[float] = None
    is_paper: bool
    pnl_usdc: Optional[float] = None
    pnl_pct: Optional[float] = None
    risk_approved: bool
    risk_rejection_reason: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_decision: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_overridden: bool = False
    created_at: datetime
    executed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    trades: List[TradeResponse]
    total: int


class ManualTradeRequest(BaseModel):
    condition_id: str
    side: str = Field(..., pattern="^(buy|sell)$")
    outcome: str = Field(..., pattern="^(Yes|No)$")
    size_usdc: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0, lt=1)
    max_slippage_pct: float = Field(default=0.02, ge=0, le=0.10)


# ── Wallet Schemas ────────────────────────────────────────────────────────────

class WalletResponse(BaseModel):
    id: str
    address: str
    label: Optional[str] = None
    is_tracked: bool
    copy_trade_enabled: bool
    total_trades: int
    win_rate: Optional[float] = None
    avg_pnl_pct: Optional[float] = None
    total_volume_usdc: float = 0.0
    ai_quality_score: Optional[float] = None
    ai_strategy_class: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_analysis_summary: Optional[str] = None
    last_trade_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AddWalletRequest(BaseModel):
    address: str
    label: Optional[str] = None
    copy_trade_enabled: bool = False
    copy_trade_max_size_usdc: float = Field(default=50.0, gt=0)
    copy_trade_size_pct: float = Field(default=0.1, gt=0, le=0.5)


# ── Signal Schemas ────────────────────────────────────────────────────────────

class SignalResponse(BaseModel):
    id: str
    strategy: str
    condition_id: str
    market_question: Optional[str] = None
    side: str
    outcome: str
    target_price: float
    suggested_size_usdc: float
    acted_on: bool
    skip_reason: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_decision: Optional[str] = None
    ai_reasoning: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Schemas ────────────────────────────────────────────────────────────────

class MarketScoreRequest(BaseModel):
    condition_id: str


class MarketScoreResponse(BaseModel):
    condition_id: str
    score: float
    reasoning: str
    tags: List[str] = []
    volatility_potential: str
    resolution_clarity: str
    recommended_action: str
    key_risk: str
    is_fallback: bool = False
    cache_hit: bool = False


class TradeFilterRequest(BaseModel):
    condition_id: str
    strategy: str
    side: str
    outcome: str
    target_price: float
    suggested_size_usdc: float


class TradeFilterResponse(BaseModel):
    confidence: float
    decision: str
    size_modifier: float
    reasoning: str
    key_concern: Optional[str] = None
    urgency: str
    is_fallback: bool = False


class OptimizationSuggestion(BaseModel):
    parameter: str
    current_value: Any
    suggested_value: Any
    change_pct: float
    rationale: str
    confidence: float
    expected_impact: str


class OptimizationResponse(BaseModel):
    suggestions: List[OptimizationSuggestion]
    overall_assessment: str
    priority: str
    status: str = "pending_review"
    generated_at: Optional[str] = None


# ── System Schemas ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    paper_trading: bool
    ai_enabled: bool
    ai_available: bool


class RiskParamsResponse(BaseModel):
    max_position_size_usdc: float
    max_total_exposure_usdc: float
    max_positions: int
    min_liquidity: float
    max_spread_pct: float
    max_slippage_pct: float
    paper_trading: bool
    trading_paused: bool
    pause_reason: Optional[str] = None


class UpdateRiskParamsRequest(BaseModel):
    max_position_size_usdc: Optional[float] = Field(None, gt=0)
    max_total_exposure_usdc: Optional[float] = Field(None, gt=0)
    max_positions: Optional[int] = Field(None, gt=0)
    min_liquidity: Optional[float] = Field(None, ge=0)
    max_spread_pct: Optional[float] = Field(None, gt=0, le=0.50)
    max_slippage_pct: Optional[float] = Field(None, gt=0, le=0.20)
