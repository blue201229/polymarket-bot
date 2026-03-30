from fastapi import APIRouter

from api.routes.ai import router as ai_router
from api.routes.health import router as health_router
from api.routes.markets import router as markets_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(markets_router, prefix="/markets", tags=["markets"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
