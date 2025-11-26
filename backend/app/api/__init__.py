from .routes_health import router as health_router
from .routes_webhook import router as webhook_router
from .routes_access import router as access_router
from .routes_personas import router as personas_router
from .routes_chat import router as chat_router
from .routes_payments import router as payments_router
from .routes_store import router as store_router
from .routes_analytics import router as analytics_router
from .routes_features import router as features_router
from .routes_bot_control import router as bot_control_router
from .routes_events import router as events_router

__all__ = [
    "health_router",
    "webhook_router",
    "access_router",
    "personas_router",
    "chat_router",
    "payments_router",
    "store_router",
    "analytics_router",
    "features_router",
    "bot_control_router",
    "events_router",
]
