"""
Redis-based rate limiter utility

Uses Token Bucket algorithm for rate limiting with Redis backend
"""
import time
from typing import Optional, Tuple
from shared.utils.redis import redis_client
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token Bucket rate limiter with Redis backend

    Supports multiple time windows (e.g., 10/minute, 100/hour)
    """

    def __init__(self, prefix: str = "rate_limit"):
        """
        Initialize rate limiter

        Args:
            prefix: Redis key prefix for rate limit data
        """
        self.prefix = prefix

    async def check_rate_limit(
        self,
        user_id: int,
        limit: int,
        window: int,
        resource: str = "default"
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if user is within rate limit

        Args:
            user_id: User ID to check
            limit: Maximum requests allowed
            window: Time window in seconds
            resource: Resource identifier (e.g., 'messages', 'images')

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            - is_allowed: True if request is allowed
            - retry_after: Seconds to wait before retry (None if allowed)

        Example:
            # Check if user can send message (10 per minute)
            allowed, retry = await limiter.check_rate_limit(
                user_id=123,
                limit=10,
                window=60,
                resource="messages"
            )

            if not allowed:
                await message.answer(f"Too many requests. Wait {retry}s")
        """
        key = f"{self.prefix}:{resource}:{user_id}"
        current_time = int(time.time())

        try:
            await redis_client.connect()

            # Get current count and timestamp
            data = await redis_client.get_json(key)

            if not data:
                # First request - allow and set initial data
                await redis_client.set_json(
                    key,
                    {
                        "count": 1,
                        "window_start": current_time
                    },
                    expire=window
                )
                return True, None

            count = data.get("count", 0)
            window_start = data.get("window_start", current_time)
            elapsed = current_time - window_start

            # Check if window expired - reset counter
            if elapsed >= window:
                await redis_client.set_json(
                    key,
                    {
                        "count": 1,
                        "window_start": current_time
                    },
                    expire=window
                )
                return True, None

            # Within window - check limit
            if count < limit:
                # Increment counter
                await redis_client.set_json(
                    key,
                    {
                        "count": count + 1,
                        "window_start": window_start
                    },
                    expire=window - elapsed
                )
                return True, None

            # Rate limit exceeded
            retry_after = window - elapsed
            logger.warning(
                f"Rate limit exceeded for user {user_id}, "
                f"resource={resource}, limit={limit}/{window}s, "
                f"retry_after={retry_after}s"
            )
            return False, retry_after

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request on error to avoid blocking users
            return True, None

    async def get_remaining(
        self,
        user_id: int,
        limit: int,
        window: int,
        resource: str = "default"
    ) -> int:
        """
        Get remaining requests for user

        Args:
            user_id: User ID
            limit: Maximum requests allowed
            window: Time window in seconds
            resource: Resource identifier

        Returns:
            Number of remaining requests
        """
        key = f"{self.prefix}:{resource}:{user_id}"

        try:
            data = await redis_client.get_json(key)
            if not data:
                return limit

            count = data.get("count", 0)
            return max(0, limit - count)
        except Exception as e:
            logger.error(f"Error getting remaining limit: {e}")
            return limit

    async def reset_limit(
        self,
        user_id: int,
        resource: str = "default"
    ) -> bool:
        """
        Reset rate limit for user (admin function)

        Args:
            user_id: User ID to reset
            resource: Resource identifier

        Returns:
            True if reset successful
        """
        key = f"{self.prefix}:{resource}:{user_id}"

        try:
            deleted = await redis_client.delete(key)
            logger.info(f"Rate limit reset for user {user_id}, resource={resource}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
            return False


# Global rate limiter instance
rate_limiter = RateLimiter()
