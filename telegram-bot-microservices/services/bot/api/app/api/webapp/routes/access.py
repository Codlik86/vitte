"""
Access status API routes for webapp
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from shared.database import get_db, User, Subscription, ImageBalance, AccessStatus, get_images_remaining
from app.api.webapp.dependencies import WebAppUser

router = APIRouter()


# ==================== SCHEMAS ====================

class ImagesStatus(BaseModel):
    remaining_free_today: int
    remaining_paid: int
    total_remaining: int


class AccessStatusResponse(BaseModel):
    telegram_id: int
    access_status: str
    free_messages_used: int
    free_messages_limit: int
    has_access: bool
    can_send_message: bool
    has_subscription: bool
    plan_code: Optional[str] = None
    premium_until: Optional[datetime] = None
    images: Optional[ImagesStatus] = None


# ==================== ROUTES ====================

@router.get("/access/status", response_model=AccessStatusResponse)
async def get_access_status(
    user: WebAppUser,
    db: AsyncSession = Depends(get_db)
):
    """Get user access status"""
    telegram_id = user.id

    # Reload user with relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription), selectinload(User.image_balance))
        .where(User.id == telegram_id)
    )
    user_with_rels = result.scalar_one()

    # Get subscription
    subscription = user_with_rels.subscription
    has_subscription = bool(subscription and subscription.is_active and subscription.expires_at and subscription.expires_at > datetime.now(timezone.utc))

    # Determine access status
    if has_subscription:
        access_status = AccessStatus.SUBSCRIPTION_ACTIVE.value
        has_access = True
        can_send_message = True
    elif user_with_rels.free_messages_used < user_with_rels.free_messages_limit:
        access_status = AccessStatus.TRIAL_USAGE.value
        has_access = True
        can_send_message = True
    else:
        access_status = AccessStatus.NO_ACCESS.value
        has_access = False
        can_send_message = False

    # Get image balance with automatic daily reset
    # Если новый день - сбрасываем daily_subscription_used до 0 (НЕ накапливается!)
    image_quota = await get_images_remaining(db, telegram_id)
    images = ImagesStatus(
        remaining_free_today=image_quota.remaining_daily,
        remaining_paid=image_quota.remaining_purchased,
        total_remaining=image_quota.total_remaining
    )

    return AccessStatusResponse(
        telegram_id=telegram_id,
        access_status=access_status,
        free_messages_used=user_with_rels.free_messages_used,
        free_messages_limit=user_with_rels.free_messages_limit,
        has_access=has_access,
        can_send_message=can_send_message,
        has_subscription=has_subscription,
        plan_code=subscription.plan if subscription else None,
        premium_until=subscription.expires_at if subscription else None,
        images=images
    )
