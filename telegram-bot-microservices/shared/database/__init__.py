"""Database module exports"""
from shared.database.base import Base
from shared.database.session import (
    engine,
    AsyncSessionLocal,
    get_db,
    init_db,
    close_db
)
from shared.database.models import (
    User,
    Subscription,
    Dialog,
    Message,
    Settings
)
from shared.database.services import (
    # User services
    get_user_by_id,
    get_user_by_username,
    create_user,
    update_user,
    # Subscription services
    get_subscription_by_user_id,
    create_subscription,
    update_subscription,
    increment_subscription_usage,
    # Cache utilities
    invalidate_user_cache,
    invalidate_subscription_cache
)

__all__ = [
    # Base
    "Base",
    # Session
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "close_db",
    # Models
    "User",
    "Subscription",
    "Dialog",
    "Message",
    "Settings",
    # Services (cached)
    "get_user_by_id",
    "get_user_by_username",
    "create_user",
    "update_user",
    "get_subscription_by_user_id",
    "create_subscription",
    "update_subscription",
    "increment_subscription_usage",
    "invalidate_user_cache",
    "invalidate_subscription_cache"
]
