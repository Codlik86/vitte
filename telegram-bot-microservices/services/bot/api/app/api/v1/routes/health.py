"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from shared.database import get_db
from shared.schemas import HealthResponse
from shared.utils import redis_client, get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check"""
    return HealthResponse(
        status="healthy",
        service="api",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@router.get("/health/db")
async def health_check_db():
    """Health check with database connectivity"""
    try:
        async for db in get_db():
            # Test database connection
            await db.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "service": "api",
                "database": "connected",
                "timestamp": datetime.utcnow()
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "api",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }


@router.get("/health/redis")
async def health_check_redis():
    """Health check with Redis connectivity"""
    try:
        await redis_client.connect()
        await redis_client.set("health_check", "ok", expire=10)
        value = await redis_client.get("health_check")
        
        return {
            "status": "healthy",
            "service": "api",
            "redis": "connected",
            "test_value": value,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "api",
            "redis": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint (placeholder)"""
    return {
        "api_requests_total": 0,
        "api_requests_duration_seconds": 0.0,
        "timestamp": datetime.utcnow()
    }
