from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import AccessStatus, Subscription, SubscriptionStatus, User
from .store import list_store_products
from .features import collect_feature_states


async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    stmt: Select[tuple[Subscription]] = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            or_(Subscription.valid_until.is_(None), Subscription.valid_until > datetime.utcnow()),
        )
        .order_by(Subscription.valid_until.desc().nullslast())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def ensure_paywall_variant(session: AsyncSession, user: User) -> str:
    if user.paywall_variant:
        return user.paywall_variant
    variant = secrets.choice(["A", "B"])
    user.paywall_variant = variant
    session.add(user)
    await session.flush()
    return variant


async def build_access_status(session: AsyncSession, user: User) -> dict[str, Any]:
    limit = settings.free_messages_limit
    subscription = await get_active_subscription(session, user.id)
    paywall_variant = await ensure_paywall_variant(session, user)

    has_subscription = bool(
        user.access_status == AccessStatus.SUBSCRIPTION_ACTIVE or subscription is not None
    )
    if subscription and user.access_status != AccessStatus.SUBSCRIPTION_ACTIVE:
        user.access_status = AccessStatus.SUBSCRIPTION_ACTIVE

    premium_until = subscription.valid_until if subscription else None
    plan_code = subscription.plan_code if subscription else None

    free_used = 0 if has_subscription else user.free_messages_used
    can_send_message = has_subscription or free_used < limit

    store_products = [
        {
            "product_code": product.product_code,
            "title": product.title,
            "description": product.description,
            "price_stars": product.price_stars,
            "type": product.type,
        }
        for product in list_store_products()
    ]
    feature_states = collect_feature_states(user)

    return {
        "telegram_id": user.telegram_id,
        "access_status": user.access_status,
        "free_messages_used": free_used,
        "free_messages_limit": limit,
        "can_send_message": can_send_message,
        "has_access": can_send_message,
        "has_subscription": has_subscription,
        "plan_code": plan_code,
        "premium_until": premium_until,
        "paywall_variant": paywall_variant,
        "store": {
            "available_products": store_products,
        },
        "features": {
            "features": [
                {
                    "code": feature.code,
                    "title": feature.title,
                    "description": feature.description,
                    "active": feature.active,
                    "enabled": feature.enabled,
                    "until": feature.until,
                    "product_code": feature.product_code,
                    "toggleable": feature.toggleable,
                }
                for feature in feature_states.values()
            ]
        },
    }
