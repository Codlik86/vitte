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
    Settings,
    Persona,
    UserPersona,
    ImageBalance,
    FeatureUnlock,
    Purchase,
    NotificationLog,
    Broadcast,
    BroadcastLog,
    # Enums
    AccessStatus,
    PersonaKind,
    SubscriptionStatus,
    PurchaseStatus,
    BroadcastType,
    BroadcastStatus,
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
    # Dialog services
    get_dialog_by_id,
    get_user_dialogs,
    create_dialog,
    update_dialog,
    delete_dialog,
    # Message services
    get_dialog_messages,
    create_message,
    get_message_count,
    delete_old_messages,
    # Cache utilities
    invalidate_user_cache,
    invalidate_subscription_cache
)
from shared.database.image_service import (
    ImageQuotaResult,
    check_and_reset_daily_quota,
    get_images_remaining,
    use_image_quota,
    add_purchased_images,
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
    "Persona",
    "UserPersona",
    "ImageBalance",
    "FeatureUnlock",
    "Purchase",
    "NotificationLog",
    "Broadcast",
    "BroadcastLog",
    # Enums
    "AccessStatus",
    "PersonaKind",
    "SubscriptionStatus",
    "PurchaseStatus",
    "BroadcastType",
    "BroadcastStatus",
    # User services
    "get_user_by_id",
    "get_user_by_username",
    "create_user",
    "update_user",
    # Subscription services
    "get_subscription_by_user_id",
    "create_subscription",
    "update_subscription",
    "increment_subscription_usage",
    # Dialog services
    "get_dialog_by_id",
    "get_user_dialogs",
    "create_dialog",
    "update_dialog",
    "delete_dialog",
    # Message services
    "get_dialog_messages",
    "create_message",
    "get_message_count",
    "delete_old_messages",
    # Cache utilities
    "invalidate_user_cache",
    "invalidate_subscription_cache",
    # Image quota services
    "ImageQuotaResult",
    "check_and_reset_daily_quota",
    "get_images_remaining",
    "use_image_quota",
    "add_purchased_images",
]
