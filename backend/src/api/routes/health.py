from fastapi import APIRouter

from core.config import settings

router = APIRouter()


@router.get("")
async def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
