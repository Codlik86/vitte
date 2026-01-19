"""Webapp API routes"""
from app.api.webapp.routes.personas import router as personas_router
from app.api.webapp.routes.access import router as access_router
from app.api.webapp.routes.store import router as store_router
from app.api.webapp.routes.features import router as features_router

__all__ = [
    "personas_router",
    "access_router",
    "store_router",
    "features_router"
]
