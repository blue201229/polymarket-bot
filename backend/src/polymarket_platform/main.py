import logging

from fastapi import FastAPI

from polymarket_platform.api.routes import markets
from polymarket_platform.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Polymarket AI-Assisted Trading Platform",
    description="Shared backend: deterministic trading rules + optional AI assistant layer.",
    version="0.1.0",
)

app.include_router(markets.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "ai_enabled": str(settings.ai_enabled),
    }
