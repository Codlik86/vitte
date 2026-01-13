"""API v1 module"""
from fastapi import APIRouter
from app.api.v1.routes import health_router, subscriptions_router, dialogs_router

# Create v1 router
router = APIRouter(prefix="/api/v1")

# Include routers
router.include_router(health_router, tags=["health"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(dialogs_router, prefix="/dialogs", tags=["dialogs"])

__all__ = ["router"]
