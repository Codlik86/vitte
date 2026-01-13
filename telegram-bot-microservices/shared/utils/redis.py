"""
Redis client utility with caching support
"""
import os
import json
import redis.asyncio as aioredis
from typing import Optional, Any, Dict
from datetime import datetime, date
from decimal import Decimal


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class RedisClient:
    """Redis client wrapper with caching support"""

    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

    async def connect(self):
        """Connect to Redis with connection pool"""
        if not self.client:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5
            )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self.client = None

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.client:
            await self.connect()
        value = await self.client.get(key)
        if value:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
        return value

    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set value with optional expiration (TTL in seconds)"""
        if not self.client:
            await self.connect()
        await self.client.set(key, value, ex=expire)
        self._stats["sets"] += 1

    async def delete(self, key: str) -> int:
        """Delete key, returns number of keys deleted"""
        if not self.client:
            await self.connect()
        deleted = await self.client.delete(key)
        self._stats["deletes"] += 1
        return deleted

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (e.g., 'user:*')"""
        if not self.client:
            await self.connect()

        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            deleted = await self.client.delete(*keys)
            self._stats["deletes"] += deleted
            return deleted
        return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            await self.connect()
        return await self.client.exists(key) > 0

    # JSON caching methods

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value by key and deserialize"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: Dict[str, Any], expire: Optional[int] = None):
        """Serialize and set JSON value with optional expiration"""
        json_str = json.dumps(value, cls=DateTimeEncoder)
        await self.set(key, json_str, expire=expire)

    async def get_many(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Get multiple keys at once"""
        if not self.client:
            await self.connect()

        if not keys:
            return {}

        values = await self.client.mget(keys)
        result = {}
        for key, value in zip(keys, values):
            result[key] = value
            if value:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1
        return result

    async def set_many(self, mapping: Dict[str, str], expire: Optional[int] = None):
        """Set multiple keys at once"""
        if not self.client:
            await self.connect()

        if not mapping:
            return

        # Use pipeline for atomic operations
        async with self.client.pipeline() as pipe:
            for key, value in mapping.items():
                if expire:
                    pipe.setex(key, expire, value)
                else:
                    pipe.set(key, value)
            await pipe.execute()

        self._stats["sets"] += len(mapping)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.client:
            await self.connect()
        return await self.client.incrby(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key"""
        if not self.client:
            await self.connect()
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get TTL of key (-1 if no expire, -2 if not exists)"""
        if not self.client:
            await self.connect()
        return await self.client.ttl(key)

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2)
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }


# Global redis client instance
redis_client = RedisClient()
