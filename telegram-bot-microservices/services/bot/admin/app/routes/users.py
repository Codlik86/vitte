"""
User management routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from shared.database import User, get_db
from shared.schemas import UserResponse
from shared.utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100):
    """List all users"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(User)
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            users = result.scalars().all()
            return users
            
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get user by ID"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return user
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
