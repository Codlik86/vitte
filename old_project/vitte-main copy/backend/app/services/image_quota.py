from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ImageBalance, User

DAILY_SUBSCRIPTION_QUOTA = 20


async def _ensure_balance(session: AsyncSession, user: User) -> ImageBalance:
    result = await session.execute(select(ImageBalance).where(ImageBalance.user_id == user.id))
    balance = result.scalar_one_or_none()
    if balance:
        return balance
    balance = ImageBalance(
        user_id=user.id,
        total_purchased_images=0,
        remaining_purchased_images=0,
        daily_subscription_quota=DAILY_SUBSCRIPTION_QUOTA,
        daily_subscription_used=0,
        daily_quota_date=datetime.utcnow(),
    )
    session.add(balance)
    await session.flush()
    return balance


def _reset_daily_if_needed(balance: ImageBalance) -> None:
    today = date.today()
    if balance.daily_quota_date is None or balance.daily_quota_date.date() != today:
        balance.daily_subscription_used = 0
        balance.daily_quota_date = datetime.utcnow()


async def get_image_quota(session: AsyncSession, user: User, has_subscription: bool) -> dict:
    balance = await _ensure_balance(session, user)
    _reset_daily_if_needed(balance)
    remaining_free_today = max(balance.daily_subscription_quota - balance.daily_subscription_used, 0) if has_subscription else 0
    remaining_paid = max(balance.remaining_purchased_images, 0)
    total_remaining = remaining_free_today + remaining_paid
    return {
        "remaining_free_today": remaining_free_today,
        "remaining_paid": remaining_paid,
        "total_remaining": total_remaining,
    }


async def consume_image(session: AsyncSession, user: User, count: int = 1, has_subscription: bool = False) -> None:
    if count <= 0:
        return
    balance = await _ensure_balance(session, user)
    _reset_daily_if_needed(balance)

    free_left = max(balance.daily_subscription_quota - balance.daily_subscription_used, 0) if has_subscription else 0
    to_consume = count

    # Consume daily quota first
    use_from_free = min(free_left, to_consume)
    balance.daily_subscription_used += use_from_free
    to_consume -= use_from_free

    if to_consume > 0:
        if balance.remaining_purchased_images < to_consume:
            raise ValueError("Not enough image quota")
        balance.remaining_purchased_images -= to_consume

    await session.flush()
