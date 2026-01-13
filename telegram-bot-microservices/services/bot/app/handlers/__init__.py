"""Handlers module"""
from app.handlers.start import router as start_router
from app.handlers.help import router as help_router
from app.handlers.status import router as status_router

__all__ = ["start_router", "help_router", "status_router"]
