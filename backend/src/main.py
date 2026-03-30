"""
Polymarket AI Trading Platform — Backend Entry Point

FastAPI application with:
- REST API (markets, trades, wallets, AI)
- WebSocket real-time feed
- Background workers (market discovery, wallet watcher, strategy runner)
- Lifespan management (DB init, Redis, WebSocket feed)
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.core.config import settings
from src.core.database import create_tables
from src.core.logging import configure_logging, get_logger
from src.core.redis_client import close_redis
from src.api.routes import markets, trades, wallets, ai, system
from src.api.websocket import websocket_endpoint

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown lifecycle."""
    configure_logging()
    logger.info(
        "platform_starting",
        env=settings.app_env,
        paper_trading=settings.paper_trading_mode,
        ai_available=settings.ai_available,
    )

    # Initialize database tables
    try:
        await create_tables()
    except Exception as e:
        logger.warning("db_init_failed", error=str(e))

    # Start background workers
    workers = []

    # Market discovery worker (runs every 10 minutes)
    workers.append(asyncio.create_task(_market_discovery_worker()))

    # Wallet watcher (Phase 3 — starts but does nothing until wallets are added)
    from src.services.wallet_watcher import WalletWatcher
    watcher = WalletWatcher()
    workers.append(asyncio.create_task(watcher.start()))

    # WebSocket market feed
    from src.data.websocket_feed import get_market_feed
    feed = get_market_feed()
    workers.append(asyncio.create_task(feed.start()))

    logger.info("platform_started", workers=len(workers))

    yield  # Application runs here

    # Shutdown
    logger.info("platform_shutting_down")
    for task in workers:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    await close_redis()
    logger.info("platform_stopped")


app = FastAPI(
    title="Polymarket AI Trading Platform",
    description="Production-grade prediction market trading with AI-assisted decision making",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(system.router, prefix="/api/v1")
app.include_router(markets.router, prefix="/api/v1")
app.include_router(trades.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.websocket("/ws")
async def websocket_route(ws: WebSocket):
    await websocket_endpoint(ws)


@app.get("/")
async def root():
    return {
        "name": "Polymarket AI Trading Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/system/health",
    }


# ── Background Workers ────────────────────────────────────────────────────────

async def _market_discovery_worker() -> None:
    """Periodically discover and score new markets."""
    from src.services.market_service import MarketService

    service = MarketService()
    while True:
        try:
            result = await service.discover_and_score_markets(
                limit=200,
                min_volume=500,
                score_with_ai=settings.ai_available,
            )
            logger.info("market_discovery_cycle", **result)
        except Exception as e:
            logger.error("market_discovery_worker_error", error=str(e))

        await asyncio.sleep(600)  # Every 10 minutes
