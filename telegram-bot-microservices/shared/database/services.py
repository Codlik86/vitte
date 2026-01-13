"""
Database service layer with caching

This module provides cached functions for database operations.
All read operations are cached, write operations invalidate caches.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User, Subscription, Dialog, Message
from shared.utils import (
    cached,
    cache_invalidate,
    TTL_5_MINUTES,
    TTL_10_MINUTES,
    TTL_1_HOUR,
    get_logger
)

logger = get_logger(__name__)


# ==================== USER SERVICES ====================

@cached(ttl=TTL_5_MINUTES, prefix="user")
async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get user by ID with 5-minute cache

    Args:
        db: Database session
        user_id: Telegram user ID

    Returns:
        User object or None

    Cache key: user:{user_id}
    TTL: 5 minutes
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        logger.debug(f"User {user_id} loaded from DB (will be cached)")

    return user


@cached(ttl=TTL_5_MINUTES, prefix="user_username")
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username with 5-minute cache

    Args:
        db: Database session
        username: Telegram username

    Returns:
        User object or None

    Cache key: user_username:{username}
    TTL: 5 minutes
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: str = "ru"
) -> User:
    """
    Create new user and auto-cache it

    Args:
        db: Database session
        user_id: Telegram user ID
        username: Telegram username
        first_name: First name
        last_name: Last name
        language_code: Language code

    Returns:
        Created User object
    """
    user = User(
        id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"New user created: {user_id}")

    # Cache the newly created user
    from shared.utils import redis_client, model_to_dict
    user_dict = model_to_dict(user)
    await redis_client.set_json(f"user:{user_id}", user_dict, expire=TTL_5_MINUTES)

    return user


async def update_user(db: AsyncSession, user_id: int, **kwargs) -> Optional[User]:
    """
    Update user and invalidate cache

    Args:
        db: Database session
        user_id: User ID to update
        **kwargs: Fields to update

    Returns:
        Updated User object or None
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Update fields
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    # Invalidate cache
    await cache_invalidate("user", user_id)
    if user.username:
        await cache_invalidate("user_username", user.username)

    logger.info(f"User {user_id} updated and cache invalidated")

    return user


# ==================== SUBSCRIPTION SERVICES ====================

@cached(ttl=TTL_1_HOUR, prefix="subscription")
async def get_subscription_by_user_id(db: AsyncSession, user_id: int) -> Optional[Subscription]:
    """
    Get subscription by user ID with 1-hour cache

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Subscription object or None

    Cache key: subscription:{user_id}
    TTL: 1 hour
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        logger.debug(f"Subscription for user {user_id} loaded from DB (will be cached)")

    return subscription


async def create_subscription(
    db: AsyncSession,
    user_id: int,
    plan: str = "free",
    is_active: bool = True,
    messages_limit: int = 100,
    images_limit: int = 10
) -> Subscription:
    """
    Create new subscription and auto-cache it

    Args:
        db: Database session
        user_id: User ID
        plan: Subscription plan (free, premium, enterprise)
        is_active: Is subscription active
        messages_limit: Messages limit
        images_limit: Images limit

    Returns:
        Created Subscription object
    """
    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        is_active=is_active,
        messages_limit=messages_limit,
        images_limit=images_limit
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Subscription created for user {user_id}")

    # Cache the newly created subscription
    from shared.utils import redis_client, model_to_dict
    sub_dict = model_to_dict(subscription)
    await redis_client.set_json(f"subscription:{user_id}", sub_dict, expire=TTL_1_HOUR)

    return subscription


async def update_subscription(
    db: AsyncSession,
    user_id: int,
    **kwargs
) -> Optional[Subscription]:
    """
    Update subscription and invalidate cache

    Args:
        db: Database session
        user_id: User ID
        **kwargs: Fields to update

    Returns:
        Updated Subscription object or None
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    # Update fields
    for key, value in kwargs.items():
        if hasattr(subscription, key):
            setattr(subscription, key, value)

    await db.commit()
    await db.refresh(subscription)

    # Invalidate cache
    await cache_invalidate("subscription", user_id)

    logger.info(f"Subscription for user {user_id} updated and cache invalidated")

    return subscription


async def increment_subscription_usage(
    db: AsyncSession,
    user_id: int,
    messages: int = 0,
    images: int = 0
) -> Optional[Subscription]:
    """
    Increment subscription usage counters and invalidate cache

    Args:
        db: Database session
        user_id: User ID
        messages: Number of messages to add
        images: Number of images to add

    Returns:
        Updated Subscription object or None
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    # Increment counters
    if messages > 0:
        subscription.messages_used = (subscription.messages_used or 0) + messages
    if images > 0:
        subscription.images_used = (subscription.images_used or 0) + images

    await db.commit()
    await db.refresh(subscription)

    # Invalidate cache
    await cache_invalidate("subscription", user_id)

    logger.debug(f"Subscription usage incremented for user {user_id}")

    return subscription


# ==================== CACHE UTILITIES ====================

async def invalidate_user_cache(user_id: int, username: Optional[str] = None):
    """
    Manually invalidate user cache

    Use this when user data changes outside of service layer
    """
    await cache_invalidate("user", user_id)
    if username:
        await cache_invalidate("user_username", username)
    logger.debug(f"User cache invalidated for {user_id}")


async def invalidate_subscription_cache(user_id: int):
    """
    Manually invalidate subscription cache

    Use this when subscription changes outside of service layer
    """
    await cache_invalidate("subscription", user_id)
    logger.debug(f"Subscription cache invalidated for user {user_id}")


# ==================== DIALOG SERVICES ====================

@cached(ttl=TTL_10_MINUTES, prefix="dialog")
async def get_dialog_by_id(db: AsyncSession, dialog_id: int) -> Optional[Dialog]:
    """
    Get dialog by ID with 10-minute cache

    Args:
        db: Database session
        dialog_id: Dialog ID

    Returns:
        Dialog object or None

    Cache key: dialog:{dialog_id}
    TTL: 10 minutes
    """
    result = await db.execute(
        select(Dialog).where(Dialog.id == dialog_id)
    )
    dialog = result.scalar_one_or_none()

    if dialog:
        logger.debug(f"Dialog {dialog_id} loaded from DB (will be cached)")

    return dialog


async def get_user_dialogs(
    db: AsyncSession,
    user_id: int,
    active_only: bool = True,
    limit: int = 50
) -> list[Dialog]:
    """
    Get all dialogs for user

    Args:
        db: Database session
        user_id: User ID
        active_only: Return only active dialogs
        limit: Maximum dialogs to return

    Returns:
        List of Dialog objects
    """
    query = select(Dialog).where(Dialog.user_id == user_id)

    if active_only:
        query = query.where(Dialog.is_active == True)

    query = query.order_by(Dialog.updated_at.desc()).limit(limit)

    result = await db.execute(query)
    dialogs = result.scalars().all()

    logger.debug(f"Loaded {len(dialogs)} dialogs for user {user_id}")
    return list(dialogs)


async def create_dialog(
    db: AsyncSession,
    user_id: int,
    title: Optional[str] = None
) -> Dialog:
    """
    Create new dialog

    Args:
        db: Database session
        user_id: User ID
        title: Dialog title (optional)

    Returns:
        Created Dialog object
    """
    dialog = Dialog(
        user_id=user_id,
        title=title or f"Dialog {int(time.time())}"
    )
    db.add(dialog)
    await db.commit()
    await db.refresh(dialog)

    logger.info(f"Dialog created: id={dialog.id}, user_id={user_id}")

    # Cache the newly created dialog
    from shared.utils import redis_client, model_to_dict
    import time
    dialog_dict = model_to_dict(dialog)
    await redis_client.set_json(f"dialog:{dialog.id}", dialog_dict, expire=TTL_10_MINUTES)

    return dialog


async def update_dialog(
    db: AsyncSession,
    dialog_id: int,
    **kwargs
) -> Optional[Dialog]:
    """
    Update dialog and invalidate cache

    Args:
        db: Database session
        dialog_id: Dialog ID
        **kwargs: Fields to update

    Returns:
        Updated Dialog object or None
    """
    result = await db.execute(
        select(Dialog).where(Dialog.id == dialog_id)
    )
    dialog = result.scalar_one_or_none()

    if not dialog:
        return None

    # Update fields
    for key, value in kwargs.items():
        if hasattr(dialog, key):
            setattr(dialog, key, value)

    await db.commit()
    await db.refresh(dialog)

    # Invalidate cache
    await cache_invalidate("dialog", dialog_id)

    logger.info(f"Dialog {dialog_id} updated and cache invalidated")

    return dialog


async def delete_dialog(db: AsyncSession, dialog_id: int) -> bool:
    """
    Mark dialog as inactive (soft delete)

    Args:
        db: Database session
        dialog_id: Dialog ID

    Returns:
        True if deleted successfully
    """
    dialog = await update_dialog(db, dialog_id, is_active=False)
    return dialog is not None


# ==================== MESSAGE SERVICES ====================

async def get_dialog_messages(
    db: AsyncSession,
    dialog_id: int,
    limit: int = 100,
    offset: int = 0
) -> list[Message]:
    """
    Get messages for dialog

    Args:
        db: Database session
        dialog_id: Dialog ID
        limit: Maximum messages to return
        offset: Offset for pagination

    Returns:
        List of Message objects (ordered by created_at ASC)
    """
    query = (
        select(Message)
        .where(Message.dialog_id == dialog_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    logger.debug(f"Loaded {len(messages)} messages for dialog {dialog_id}")
    return list(messages)


async def create_message(
    db: AsyncSession,
    dialog_id: int,
    role: str,
    content: str,
    extra_data: Optional[dict] = None
) -> Message:
    """
    Create new message in dialog

    Args:
        db: Database session
        dialog_id: Dialog ID
        role: Message role (user, assistant, system)
        content: Message content
        extra_data: Optional metadata

    Returns:
        Created Message object
    """
    message = Message(
        dialog_id=dialog_id,
        role=role,
        content=content,
        extra_data=extra_data
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    logger.debug(f"Message created: id={message.id}, dialog_id={dialog_id}, role={role}")

    return message


async def get_message_count(db: AsyncSession, dialog_id: int) -> int:
    """
    Get total message count for dialog

    Args:
        db: Database session
        dialog_id: Dialog ID

    Returns:
        Total message count
    """
    from sqlalchemy import func

    query = select(func.count(Message.id)).where(Message.dialog_id == dialog_id)
    result = await db.execute(query)
    count = result.scalar() or 0

    return count


async def delete_old_messages(
    db: AsyncSession,
    dialog_id: int,
    keep_last: int = 50
) -> int:
    """
    Delete old messages from dialog (keep last N)

    Args:
        db: Database session
        dialog_id: Dialog ID
        keep_last: Number of messages to keep

    Returns:
        Number of deleted messages
    """
    from sqlalchemy import delete

    # Get IDs of messages to keep
    keep_query = (
        select(Message.id)
        .where(Message.dialog_id == dialog_id)
        .order_by(Message.created_at.desc())
        .limit(keep_last)
    )
    result = await db.execute(keep_query)
    keep_ids = [row[0] for row in result.all()]

    if not keep_ids:
        return 0

    # Delete messages not in keep list
    delete_query = (
        delete(Message)
        .where(Message.dialog_id == dialog_id)
        .where(Message.id.notin_(keep_ids))
    )
    result = await db.execute(delete_query)
    deleted_count = result.rowcount

    await db.commit()

    logger.info(f"Deleted {deleted_count} old messages from dialog {dialog_id}")

    return deleted_count
