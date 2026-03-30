from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health() -> dict[str, str]:
    return {"status": "ok"}
