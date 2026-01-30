"""
Dashboard routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import User, Subscription, get_db
from shared.utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def dashboard_home():
    """Admin dashboard home"""
    return {
        "title": "Vitte Bot Admin Panel",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        async for db in get_db():
            # Count total users
            total_users = await db.scalar(select(func.count(User.id)))
            
            # Count active users
            active_users = await db.scalar(
                select(func.count(User.id)).where(User.is_active == True)
            )
            
            # Count premium subscriptions
            premium_subs = await db.scalar(
                select(func.count(Subscription.id)).where(
                    Subscription.plan != "free",
                    Subscription.is_active == True
                )
            )
            
            return {
                "total_users": total_users or 0,
                "active_users": active_users or 0,
                "premium_subscriptions": premium_subs or 0
            }
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "total_users": 0,
            "active_users": 0,
            "premium_subscriptions": 0,
            "error": str(e)
        }


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "admin"
    }
