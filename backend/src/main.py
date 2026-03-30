from fastapi import FastAPI

from api.router import api_router
from core.config import get_settings
from core.logging_utils import setup_logging


setup_logging()
settings = get_settings()

app = FastAPI(
    title="Polymarket AI-Assisted Trading Platform API",
    version="0.1.0",
    description=(
        "Shared backend for Telegram/Discord/Web/Mobile clients. "
        "Deterministic trading and risk controls are authoritative; AI is advisory."
    ),
)
app.include_router(api_router, prefix=settings.api_prefix)

