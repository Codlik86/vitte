"""
Webapp API dependencies

Provides get_or_create_user dependency for automatic user creation
when webapp is accessed for the first time.
"""
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from shared.database import get_db, User
from shared.utils import redis_client, get_logger, TTL_5_MINUTES

logger = get_logger(__name__)

# Cache key prefix for user existence check
USER_CACHE_PREFIX = "webapp_user"


async def get_or_create_user(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get existing user or create new one with defaults.

    Uses Redis cache to minimize database queries:
    1. Check Redis cache for user existence (~1-2ms)
    2. If cached, fetch from DB (user guaranteed to exist)
    3. If not cached, check DB and create if needed
    4. Cache the user ID for 5 minutes

    Args:
        telegram_id: Telegram user ID from query parameter
        db: Database session

    Returns:
        User object (either existing or newly created)
    """
    cache_key = f"{USER_CACHE_PREFIX}:{telegram_id}"

    # Check Redis cache first
    cached = await redis_client.get(cache_key)

    if cached:
        # User exists in cache, fetch from DB
        user = await db.get(User, telegram_id)
        if user:
            return user
        # Cache was stale, continue to create user

    # Check database
    user = await db.get(User, telegram_id)

    if user:
        # User exists, cache and return
        await redis_client.set(cache_key, "1", expire=TTL_5_MINUTES)
        return user

    # Create new user with defaults
    logger.info(f"Creating new user from webapp: {telegram_id}")

    user = User(
        id=telegram_id,
        access_status="trial_usage",
        free_messages_used=0,
        free_messages_limit=10,
        is_active=True,
        is_blocked=False,
        is_admin=False,
        has_seen_welcome=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Cache the user
    await redis_client.set(cache_key, "1", expire=TTL_5_MINUTES)

    logger.info(f"Created new user {telegram_id} from webapp")

    return user


# Type alias for use in route functions
WebAppUser = Annotated[User, Depends(get_or_create_user)]
