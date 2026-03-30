from fastapi import APIRouter

from app.services.platform_blueprint import PlatformBlueprintService

router = APIRouter(prefix="/platform", tags=["platform"])
service = PlatformBlueprintService()


@router.get("/blueprint")
async def get_blueprint() -> dict:
    return service.get_blueprint()
