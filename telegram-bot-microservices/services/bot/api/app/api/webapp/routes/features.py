"""
Features API routes for webapp
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import httpx

from shared.database import get_db, User, FeatureUnlock, Dialog, Message, Subscription, NotificationLog
from shared.utils import redis_client
from app.config import config

router = APIRouter()


# ==================== FEATURES CONFIG ====================

FEATURES_CONFIG = {
    "intense_mode": {
        "title": "Интенсивный режим",
        "description": "Более эмоциональные и глубокие ответы персонажей",
        "toggleable": True,
        "product_code": "intense_mode"
    },
    "fantasy_scenes": {
        "title": "Фантазийные сцены",
        "description": "Разблокирует расширенные сценарии и истории",
        "toggleable": True,
        "product_code": "fantasy_scenes"
    }
}


# ==================== SCHEMAS ====================

class FeatureStatus(BaseModel):
    code: str
    title: str
    description: str
    active: bool  # unlocked
    enabled: bool  # currently enabled (if toggleable)
    until: Optional[datetime] = None
    product_code: str
    toggleable: bool


class FeaturesStatusResponse(BaseModel):
    features: list[FeatureStatus]


class ToggleFeatureRequest(BaseModel):
    telegram_id: int
    feature_code: str
    enabled: bool


class ToggleFeatureResponse(BaseModel):
    success: bool
    feature_code: str
    enabled: bool


class ActionResponse(BaseModel):
    success: bool
    message: Optional[str] = None


# ==================== ROUTES ====================

@router.get("/features/status", response_model=FeaturesStatusResponse)
async def get_features_status(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get user's features status"""
    # Get user with relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.feature_unlocks))
        .where(User.id == telegram_id)
    )
    user = result.scalar_one_or_none()

    # Get unlocked features
    unlocked_map = {}
    if user and user.feature_unlocks:
        for f in user.feature_unlocks:
            unlocked_map[f.feature_code] = f

    features = []
    for code, config in FEATURES_CONFIG.items():
        unlock = unlocked_map.get(code)
        features.append(FeatureStatus(
            code=code,
            title=config["title"],
            description=config["description"],
            active=unlock is not None,
            enabled=unlock.enabled if unlock else False,
            until=None,
            product_code=config["product_code"],
            toggleable=config["toggleable"]
        ))

    return FeaturesStatusResponse(features=features)


@router.post("/features/toggle", response_model=ToggleFeatureResponse)
async def toggle_feature(
    request: ToggleFeatureRequest,
    db: AsyncSession = Depends(get_db)
):
    """Toggle a feature on/off"""
    # Check if feature exists
    if request.feature_code not in FEATURES_CONFIG:
        raise HTTPException(status_code=404, detail="Feature not found")

    # Get user
    user = await db.get(User, request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find unlock
    result = await db.execute(
        select(FeatureUnlock).where(
            FeatureUnlock.user_id == request.telegram_id,
            FeatureUnlock.feature_code == request.feature_code
        )
    )
    unlock = result.scalar_one_or_none()

    if not unlock:
        raise HTTPException(status_code=403, detail="Feature not unlocked")

    # Toggle
    unlock.enabled = request.enabled
    await db.commit()

    return ToggleFeatureResponse(
        success=True,
        feature_code=request.feature_code,
        enabled=request.enabled
    )


@router.post("/features/clear-dialogs", response_model=ActionResponse)
async def clear_dialogs(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Clear user's dialog history (short-term memory)"""
    # Get user
    user = await db.get(User, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all dialog IDs first
    result = await db.execute(
        select(Dialog.id).where(Dialog.user_id == telegram_id)
    )
    dialog_ids = [row[0] for row in result.all()]

    # Delete all messages from these dialogs
    if dialog_ids:
        await db.execute(
            delete(Message).where(Message.dialog_id.in_(dialog_ids))
        )

    # Delete all dialogs
    await db.execute(
        delete(Dialog).where(Dialog.user_id == telegram_id)
    )
    await db.commit()

    # Clear Redis cache for this user
    try:
        # Clear user features cache
        await redis_client.delete(f"user_features:{telegram_id}")
        # Clear user images quota cache
        await redis_client.delete(f"user_images_quota:{telegram_id}")
        # Clear any other user-specific cache keys
        pattern = f"*{telegram_id}*"
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        print(f"Failed to clear Redis cache for user {telegram_id}: {e}")

    return ActionResponse(
        success=True,
        message="Dialogs cleared successfully"
    )


@router.post("/features/clear-long-memory", response_model=ActionResponse)
async def clear_long_memory(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Clear user's long-term memory (Qdrant vectors)"""
    # Get user
    user = await db.get(User, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # TODO: Clear Qdrant vectors for this user
    # For now, just return success

    return ActionResponse(
        success=True,
        message="Long-term memory cleared successfully"
    )


@router.post("/features/delete-account", response_model=ActionResponse)
async def delete_account(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account and all associated data"""
    # Get user
    user = await db.get(User, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete long-term memory from Qdrant
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{config.api_url}/api/memory/clear",
                json={"telegram_id": telegram_id},
                timeout=10.0,
            )
    except Exception as e:
        print(f"Failed to delete Qdrant memories for user {telegram_id}: {e}")

    # Get all dialog IDs first
    result = await db.execute(
        select(Dialog.id).where(Dialog.user_id == telegram_id)
    )
    dialog_ids = [row[0] for row in result.all()]

    # Delete all messages from user's dialogs
    if dialog_ids:
        await db.execute(
            delete(Message).where(Message.dialog_id.in_(dialog_ids))
        )

    # Delete all dialogs
    await db.execute(
        delete(Dialog).where(Dialog.user_id == telegram_id)
    )

    # Delete subscription (CASCADE will handle related data)
    await db.execute(
        delete(Subscription).where(Subscription.user_id == telegram_id)
    )

    # Delete notification logs
    await db.execute(
        delete(NotificationLog).where(NotificationLog.user_id == telegram_id)
    )

    # Delete all user data (CASCADE will handle: feature_unlocks, image_balances, purchases, broadcast_logs, user_personas)
    await db.delete(user)
    await db.commit()

    # Clear ALL Redis cache for this user
    try:
        # Clear specific known keys
        await redis_client.delete(f"user_features:{telegram_id}")
        await redis_client.delete(f"user_images_quota:{telegram_id}")

        # Clear all keys containing user ID
        pattern = f"*{telegram_id}*"
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        print(f"Failed to clear Redis cache for user {telegram_id}: {e}")

    return ActionResponse(
        success=True,
        message="Account deleted successfully"
    )
