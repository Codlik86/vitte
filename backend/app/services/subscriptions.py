from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Subscription, SubscriptionStatus, User, AccessStatus
from ..services.payments import estimate_valid_until, get_payment_plan
from ..services.access import get_active_subscription


async def get_user_subscription_status(session: AsyncSession, user: User) -> dict:
    subscription = await get_active_subscription(session, user.id)
    if not subscription:
        return {
            "has_subscription": False,
            "until": None,
            "days_left": None,
            "plan_code": None,
        }
    until = subscription.valid_until
    days_left = None
    if until:
        days_left = max((until - datetime.utcnow()).days, 0)
    return {
        "has_subscription": True,
        "until": until,
        "days_left": days_left,
        "plan_code": subscription.plan_code,
    }


async def ensure_premium_for_user(session: AsyncSession, user: User, plan_code: str, period_days: int | None = None):
    plan = get_payment_plan(plan_code)
    now = datetime.utcnow()
    subscription = await get_active_subscription(session, user.id)
    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            provider="stars",
            plan_code=plan_code,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
        )
        session.add(subscription)
    if plan:
        subscription.valid_until = estimate_valid_until(plan, subscription.started_at or now)
    elif period_days:
        baseline = subscription.valid_until if subscription.valid_until and subscription.valid_until > now else now
        subscription.valid_until = baseline + timedelta(days=period_days)
    subscription.status = SubscriptionStatus.ACTIVE
    user.access_status = AccessStatus.SUBSCRIPTION_ACTIVE
    await session.flush()
    return subscription
