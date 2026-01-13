"""
Caching decorators and utilities
"""
import functools
import hashlib
import inspect
from typing import Optional, Callable, Any, Union
from shared.utils.redis import redis_client


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate cache key from function arguments

    Filters out AsyncSession objects from args

    Args:
        prefix: Key prefix (e.g., 'user', 'subscription')
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string like 'user:123' or 'subscription:456'
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    # Filter out AsyncSession objects
    filtered_args = [
        arg for arg in args
        if not isinstance(arg, AsyncSession)
    ]

    # Extract simple ID arguments
    if filtered_args:
        # If first arg is simple type (int, str), use it directly
        if len(filtered_args) == 1 and isinstance(filtered_args[0], (int, str)):
            return f"{prefix}:{filtered_args[0]}"

    # For complex arguments, create hash
    key_parts = [str(arg) for arg in filtered_args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)

    if len(key_string) > 100:
        # Use hash for long keys
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
        return f"{prefix}:{key_hash}"

    return f"{prefix}:{key_string}" if key_string else prefix


def cached(
    ttl: int,
    prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None
):
    """
    Cache decorator for async functions with Redis backend

    Args:
        ttl: Time to live in seconds (e.g., 300 for 5 minutes)
        prefix: Cache key prefix (e.g., 'user', 'subscription')
        key_builder: Optional custom function to build cache key

    Usage:
        @cached(ttl=300, prefix="user")
        async def get_user(user_id: int):
            # This will be cached for 5 minutes
            return await db.query(User).filter_by(id=user_id).first()

        @cached(ttl=3600, prefix="subscription")
        async def get_subscription(user_id: int):
            # This will be cached for 1 hour
            return await db.query(Subscription).filter_by(user_id=user_id).first()
    """
    def decorator(func: Callable) -> Callable:
        # Determine prefix from function name if not provided
        cache_prefix = prefix or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = generate_cache_key(cache_prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = await redis_client.get_json(cache_key)
            if cached_value is not None:
                return cached_value

            # Cache miss - call original function
            result = await func(*args, **kwargs)

            # Store in cache if result is not None
            if result is not None:
                # Convert SQLAlchemy models to dict if needed
                if hasattr(result, '__dict__') and not isinstance(result, dict):
                    # SQLAlchemy model - convert to dict
                    result_dict = {}
                    for key in result.__dict__:
                        if not key.startswith('_'):
                            value = getattr(result, key)
                            result_dict[key] = value
                    await redis_client.set_json(cache_key, result_dict, expire=ttl)
                    return result  # Return original object
                else:
                    # Already a dict or primitive
                    await redis_client.set_json(cache_key, result, expire=ttl)

            return result

        return wrapper
    return decorator


def cache_invalidate(prefix: str, *args, **kwargs):
    """
    Invalidate cache for specific key

    Usage:
        await cache_invalidate("user", user_id=123)
        # This will delete cache key "user:123"
    """
    cache_key = generate_cache_key(prefix, *args, **kwargs)
    return redis_client.delete(cache_key)


def cache_invalidate_pattern(pattern: str):
    """
    Invalidate all cache keys matching pattern

    Usage:
        await cache_invalidate_pattern("user:*")
        # This will delete all keys starting with "user:"
    """
    return redis_client.delete_pattern(pattern)


class CacheManager:
    """
    Context manager for cache operations with automatic invalidation

    Usage:
        async with CacheManager(prefix="user", key=user_id) as cache:
            # If cache exists, it will be returned
            if cache.value:
                return cache.value

            # Otherwise, compute new value
            result = await compute_expensive_operation()

            # Set cache with TTL
            await cache.set(result, ttl=300)
            return result
    """

    def __init__(self, prefix: str, *args, **kwargs):
        self.prefix = prefix
        self.cache_key = generate_cache_key(prefix, *args, **kwargs)
        self.value = None

    async def __aenter__(self):
        """Load cached value if exists"""
        self.value = await redis_client.get_json(self.cache_key)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup - nothing to do"""
        pass

    async def set(self, value: Any, ttl: int):
        """Set cache value with TTL"""
        await redis_client.set_json(self.cache_key, value, expire=ttl)
        self.value = value

    async def delete(self):
        """Delete cache entry"""
        await redis_client.delete(self.cache_key)
        self.value = None


# Cache TTL constants (in seconds)
TTL_5_MINUTES = 300
TTL_10_MINUTES = 600
TTL_30_MINUTES = 1800
TTL_1_HOUR = 3600
TTL_6_HOURS = 21600
TTL_1_DAY = 86400
