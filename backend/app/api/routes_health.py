from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health", summary="Healthcheck")
async def health():
    return {"status": "ok"}
