from fastapi import APIRouter, Depends

from app.services.ai_capability_service import AICapabilityService, get_ai_capability_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/capabilities")
async def list_capabilities(
    service: AICapabilityService = Depends(get_ai_capability_service),
) -> dict:
    return service.list_capabilities()
