from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import User, AccessStatus
from ..config import settings

router = APIRouter(prefix="/api/access", tags=["access"])


@router.get("/status")
async def access_status(
    telegram_id: int = Query(..., description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        return {
            "telegram_id": telegram_id,
            "access_status": AccessStatus.TRIAL_USAGE,
            "free_messages_used": 0,
            "free_messages_limit": settings.free_messages_limit,
            "has_access": True,
        }

    has_access = user.access_status == AccessStatus.SUBSCRIPTION_ACTIVE or (
        user.access_status == AccessStatus.TRIAL_USAGE
        and user.free_messages_used < settings.free_messages_limit
    )

    return {
        "telegram_id": telegram_id,
        "access_status": user.access_status,
        "free_messages_used": user.free_messages_used,
        "free_messages_limit": settings.free_messages_limit,
        "has_access": has_access,
    }
