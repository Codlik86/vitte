"""Handlers module"""
from app.handlers.start import router as start_router
from app.handlers.help import router as help_router
from app.handlers.status import router as status_router
from app.handlers.onboarding import router as onboarding_router
from app.handlers.menu import router as menu_router
from app.handlers.chat import router as chat_router
from app.handlers.subscription import router as subscription_router

__all__ = ["start_router", "help_router", "status_router", "onboarding_router", "menu_router", "chat_router", "subscription_router"]
