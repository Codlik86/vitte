"""API module"""
from app.api.v1 import router as v1_router
from app.api.webapp import router as webapp_router
from app.api.payments import router as payments_router

__all__ = ["v1_router", "webapp_router", "payments_router"]
