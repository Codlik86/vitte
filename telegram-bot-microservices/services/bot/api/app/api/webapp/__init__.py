"""Webapp API module"""
from fastapi import APIRouter
from app.api.webapp.routes import (
    personas_router,
    access_router,
    store_router,
    features_router,
    chat_router,
)

# Create webapp router (without version prefix - webapp expects /api/*)
router = APIRouter(prefix="/api")

# Include routers
router.include_router(personas_router, tags=["personas"])
router.include_router(access_router, tags=["access"])
router.include_router(store_router, tags=["store"])
router.include_router(features_router, tags=["features"])
router.include_router(chat_router, tags=["chat"])

__all__ = ["router"]
