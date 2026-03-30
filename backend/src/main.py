from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.config import settings
from backend.src.core.database import init_db
from backend.src.core.logging import setup_logging, get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "Starting Polymarket AI Platform",
        environment=settings.environment.value,
        paper_trading=settings.paper_trading,
        ai_enabled=settings.ai_enabled,
    )

    await init_db()
    logger.info("Database initialized")

    yield

    from backend.src.utils.http_client import close_http_client
    await close_http_client()
    logger.info("Platform shutdown complete")


app = FastAPI(
    title="Polymarket AI Trading Platform",
    description="AI-assisted prediction market trading platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.src.api.routes import markets, trades, positions, wallets, ai, performance, alerts, system

app.include_router(markets.router, prefix="/api/v1")
app.include_router(trades.router, prefix="/api/v1")
app.include_router(positions.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "Polymarket AI Trading Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/system/health",
    }
