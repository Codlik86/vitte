"""
Redis client utility
"""
import os
import redis.asyncio as aioredis
from typing import Optional


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    async def connect(self):
        """Connect to Redis"""
        if not self.client:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.client:
            await self.connect()
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set value with optional expiration"""
        if not self.client:
            await self.connect()
        await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """Delete key"""
        if not self.client:
            await self.connect()
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            await self.connect()
        return await self.client.exists(key) > 0


# Global redis client instance
redis_client = RedisClient()
