"""
Redis cache for LLM responses
"""
import hashlib
import json
import logging
from typing import Optional, List
import redis.asyncio as aioredis

from app.config import settings
from app.schemas.chat import Message

logger = logging.getLogger(__name__)


class LLMCache:
    """Redis-based cache for LLM responses"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.enabled = settings.cache_enabled
        self.ttl = settings.cache_ttl

    async def connect(self):
        """Connect to Redis"""
        if not self.enabled:
            logger.info("Cache disabled")
            return

        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info(f"Connected to Redis: {settings.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    def _generate_cache_key(
        self,
        messages: List[Message],
        model: str,
        temperature: float
    ) -> str:
        """
        Generate cache key from request parameters

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature parameter

        Returns:
            str: Cache key (hash)
        """
        # Serialize messages to JSON
        messages_json = json.dumps(
            [m.model_dump() for m in messages],
            sort_keys=True
        )

        # Create hash from messages + model + temperature
        hash_input = f"{messages_json}:{model}:{temperature}"
        cache_key = hashlib.sha256(hash_input.encode()).hexdigest()

        return f"llm:completion:{cache_key}"

    async def get(
        self,
        messages: List[Message],
        model: str,
        temperature: float
    ) -> Optional[str]:
        """
        Get cached response

        Returns:
            str | None: Cached response or None if cache miss
        """
        if not self.enabled or not self.redis:
            return None

        try:
            cache_key = self._generate_cache_key(messages, model, temperature)
            cached = await self.redis.get(cache_key)

            if cached:
                logger.info(f"Cache HIT: {cache_key[:16]}...")
                return cached
            else:
                logger.debug(f"Cache MISS: {cache_key[:16]}...")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        messages: List[Message],
        model: str,
        temperature: float,
        response: str
    ):
        """
        Cache response

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature
            response: LLM response to cache
        """
        if not self.enabled or not self.redis:
            return

        try:
            cache_key = self._generate_cache_key(messages, model, temperature)
            await self.redis.setex(
                cache_key,
                self.ttl,
                response
            )
            logger.info(f"Cached response: {cache_key[:16]}... (TTL={self.ttl}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def invalidate_pattern(self, pattern: str = "llm:completion:*"):
        """
        Invalidate cache by pattern

        Args:
            pattern: Redis key pattern (e.g., "llm:completion:*")
        """
        if not self.enabled or not self.redis:
            return

        try:
            cursor = 0
            count = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                    count += len(keys)

                if cursor == 0:
                    break

            logger.info(f"Invalidated {count} cache keys matching '{pattern}'")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")


# Singleton instance
llm_cache = LLMCache()
