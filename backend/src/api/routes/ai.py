from __future__ import annotations

from fastapi import APIRouter

from ai.ai_engine import AIEngine
from ai.anomaly_detector import detect_anomaly
from ai.optimizer import suggest_parameter_tuning
from ai.scoring import score_market
from ai.trade_filter import filter_trade_signal
from ai.wallet_analysis import analyze_wallet
from core.models import (
    AIExplanation,
    AIStatusResponse,
    AITradeFilterRequest,
    AITradeFilterResponse,
    AIWalletRequest,
    AIWalletResponse,
    AnomalyResponse,
    Market,
    MarketScoreResult,
    ParameterSuggestionRequest,
    ParameterSuggestionResponse,
)

router = APIRouter()
engine = AIEngine()


@router.get("/status", response_model=AIStatusResponse)
async def ai_status() -> AIStatusResponse:
    return AIStatusResponse(
        enabled=engine.enabled,
        timeout_seconds=engine.timeout_seconds,
        max_batch_size=engine.max_batch_size,
        cache_ttl_seconds=engine.cache_ttl_seconds,
    )


@router.post("/score-market", response_model=MarketScoreResult)
async def ai_score_market(market: Market) -> MarketScoreResult:
    return await score_market(engine, market)


@router.post("/wallet-analysis", response_model=AIWalletResponse)
async def ai_wallet_analysis(req: AIWalletRequest) -> AIWalletResponse:
    return await analyze_wallet(engine, req)


@router.post("/trade-filter", response_model=AITradeFilterResponse)
async def ai_trade_filter(req: AITradeFilterRequest) -> AITradeFilterResponse:
    return await filter_trade_signal(engine, req)


@router.post("/optimize", response_model=ParameterSuggestionResponse)
async def ai_optimize(req: ParameterSuggestionRequest) -> ParameterSuggestionResponse:
    return await suggest_parameter_tuning(engine, req)


@router.post("/anomaly", response_model=AnomalyResponse)
async def ai_anomaly(req: AIExplanation) -> AnomalyResponse:
    return await detect_anomaly(engine, req)
