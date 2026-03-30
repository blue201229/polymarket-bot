from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title="Polymarket AI Platform Backend",
    version="0.1.0",
    description=(
        "Shared backend for an AI-assisted trading platform. "
        "Deterministic market logic remains authoritative; AI is advisory only."
    ),
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/healthz", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
