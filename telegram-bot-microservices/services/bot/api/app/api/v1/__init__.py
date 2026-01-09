"""API v1 module"""
from fastapi import APIRouter
from app.api.v1.routes import health_router

# Create v1 router
router = APIRouter(prefix="/api/v1")
router.include_router(health_router, tags=["health"])

__all__ = ["router"]
