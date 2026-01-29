"""Admin routes"""
from app.routes.dashboard import router as dashboard_router
from app.routes.users import router as users_router
from app.routes.broadcast import router as broadcast_router

__all__ = ["dashboard_router", "users_router", "broadcast_router"]
