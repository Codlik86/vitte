"""API v1 routes"""
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.subscriptions import router as subscriptions_router
from app.api.v1.routes.dialogs import router as dialogs_router

__all__ = [
    "health_router",
    "subscriptions_router",
    "dialogs_router",
]
