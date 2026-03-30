from fastapi import APIRouter

from app.api.routes import ai, health, markets, platform

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(platform.router)
api_router.include_router(markets.router)
api_router.include_router(ai.router)
