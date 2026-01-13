"""
Subscription API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db, get_subscription_by_user_id, update_subscription
from shared.schemas import SubscriptionResponse, SubscriptionUpdate

router = APIRouter()


@router.get("/{user_id}", response_model=SubscriptionResponse)
async def get_user_subscription(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription for user

    Args:
        user_id: Telegram user ID
        db: Database session

    Returns:
        Subscription data
    """
    async for session in get_db():
        subscription = await get_subscription_by_user_id(session, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return subscription


@router.patch("/{user_id}", response_model=SubscriptionResponse)
async def update_user_subscription(
    user_id: int,
    data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update subscription for user

    Args:
        user_id: Telegram user ID
        data: Update data
        db: Database session

    Returns:
        Updated subscription data
    """
    async for session in get_db():
        # Build update dict from non-None fields
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        subscription = await update_subscription(session, user_id, **update_data)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return subscription
