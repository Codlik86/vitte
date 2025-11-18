from .routes_health import router as health_router
from .routes_webhook import router as webhook_router
from .routes_access import router as access_router
from .routes_personas import router as personas_router
from .routes_chat import router as chat_router

__all__ = ["health_router", "webhook_router", "access_router", "personas_router", "chat_router"]
