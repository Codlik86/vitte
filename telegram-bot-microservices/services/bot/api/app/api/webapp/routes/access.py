"""
Access status API routes for webapp
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from shared.database import get_db, User, Subscription, ImageBalance, AccessStatus

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
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get user access status"""
    # Get user with relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription), selectinload(User.image_balance))
        .where(User.id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Return default status for new user
        return AccessStatusResponse(
            telegram_id=telegram_id,
            access_status=AccessStatus.TRIAL_USAGE.value,
            free_messages_used=0,
            free_messages_limit=10,
            has_access=True,
            can_send_message=True,
            has_subscription=False,
            plan_code=None,
            premium_until=None,
            images=ImagesStatus(
                remaining_free_today=0,
                remaining_paid=0,
                total_remaining=0
            )
        )

    # Get subscription
    subscription = user.subscription
    has_subscription = bool(subscription and subscription.is_active and subscription.expires_at and subscription.expires_at > datetime.utcnow())

    # Determine access status
    if has_subscription:
        access_status = AccessStatus.SUBSCRIPTION_ACTIVE.value
        has_access = True
        can_send_message = True
    elif user.free_messages_used < user.free_messages_limit:
        access_status = AccessStatus.TRIAL_USAGE.value
        has_access = True
        can_send_message = True
    else:
        access_status = AccessStatus.NO_ACCESS.value
        has_access = False
        can_send_message = False

    # Get image balance
    image_balance = user.image_balance
    if image_balance:
        images = ImagesStatus(
            remaining_free_today=max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used),
            remaining_paid=image_balance.remaining_purchased_images,
            total_remaining=max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used) + image_balance.remaining_purchased_images
        )
    else:
        images = ImagesStatus(
            remaining_free_today=0,
            remaining_paid=0,
            total_remaining=0
        )

    return AccessStatusResponse(
        telegram_id=telegram_id,
        access_status=access_status,
        free_messages_used=user.free_messages_used,
        free_messages_limit=user.free_messages_limit,
        has_access=has_access,
        can_send_message=can_send_message,
        has_subscription=has_subscription,
        plan_code=subscription.plan if subscription else None,
        premium_until=subscription.expires_at if subscription else None,
        images=images
    )
