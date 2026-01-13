"""
Database service layer with caching

This module provides cached functions for database operations.
All read operations are cached, write operations invalidate caches.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User, Subscription
from shared.utils import (
    cached,
    cache_invalidate,
    TTL_5_MINUTES,
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
