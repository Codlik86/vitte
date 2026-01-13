"""Utils module exports"""
from shared.utils.logger import get_logger
from shared.utils.redis import RedisClient, redis_client, DateTimeEncoder
from shared.utils.minio import MinIOClient, minio_client
from shared.utils.rate_limiter import RateLimiter, rate_limiter
from shared.utils.cache import (
    cached,
    cache_invalidate,
    cache_invalidate_pattern,
    CacheManager,
    generate_cache_key,
    TTL_5_MINUTES,
    TTL_10_MINUTES,
    TTL_30_MINUTES,
    TTL_1_HOUR,
    TTL_6_HOURS,
    TTL_1_DAY
)
from shared.utils.serializers import (
    model_to_dict,
    models_to_dict,
    serialize_for_cache,
    get_model_cache_key,
    get_model_pattern
)

__all__ = [
    # Logger
    "get_logger",
    # Redis
    "RedisClient",
    "redis_client",
    "DateTimeEncoder",
    # Rate Limiter
    "RateLimiter",
    "rate_limiter",
    # Cache decorators and utilities
    "cached",
    "cache_invalidate",
    "cache_invalidate_pattern",
    "CacheManager",
    "generate_cache_key",
    # TTL constants
    "TTL_5_MINUTES",
    "TTL_10_MINUTES",
    "TTL_30_MINUTES",
    "TTL_1_HOUR",
    "TTL_6_HOURS",
    "TTL_1_DAY",
    # Serializers
    "model_to_dict",
    "models_to_dict",
    "serialize_for_cache",
    "get_model_cache_key",
    "get_model_pattern",
    # MinIO
    "MinIOClient",
    "minio_client"
]
