"""
Rate limiter for LLM API requests
"""
import time
import asyncio
import logging
from collections import deque

from app.config import settings

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter

    Allows bursts while maintaining average rate limit
    """

    def __init__(self, rate: int, per_seconds: int = 60):
        """
        Args:
            rate: Number of requests allowed
            per_seconds: Time window (default: 60 seconds = 1 minute)
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire token (wait if bucket is empty)

        Raises:
            asyncio.TimeoutError: If waiting too long
        """
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.last_update = now

            # Refill tokens based on time passed
            self.tokens = min(
                self.rate,
                self.tokens + (time_passed * self.rate / self.per_seconds)
            )

            if self.tokens >= 1:
                # Token available - consume it
                self.tokens -= 1
                logger.debug(f"Rate limiter: token acquired ({self.tokens:.1f} remaining)")
                return

            # No tokens - calculate wait time
            wait_time = (1 - self.tokens) * self.per_seconds / self.rate
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s...")

            await asyncio.sleep(wait_time)

            # After waiting, token should be available
            self.tokens = 0

    def get_state(self) -> dict:
        """Get rate limiter state for monitoring"""
        return {
            "rate": self.rate,
            "per_seconds": self.per_seconds,
            "tokens_available": round(self.tokens, 2),
            "last_update": self.last_update
        }


# Singleton instance
rate_limiter = TokenBucketRateLimiter(
    rate=settings.rate_limit_requests_per_minute,
    per_seconds=60
)
