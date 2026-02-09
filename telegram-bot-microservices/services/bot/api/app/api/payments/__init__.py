"""Payment routes"""
from fastapi import APIRouter
from .cryptopay import router as cryptopay_router

router = APIRouter(prefix="/payments", tags=["payments"])
router.include_router(cryptopay_router)

__all__ = ["router"]
