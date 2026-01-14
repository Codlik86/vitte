from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Subscription, SubscriptionStatus, AccessStatus
from ..schemas import PaymentPlanSchema, SubscribeRequest, SubscribeResponse
from ..services.analytics import log_event
from ..services.subscriptions import ensure_premium_for_user
from ..services.store import SUBSCRIPTION_PLANS, get_plan
from ..users_service import get_or_create_user_by_telegram_id
from ..services.telegram_id import get_or_raise_telegram_id
from ..bot import bot
from ..services.stars import send_stars_invoice_for_subscription

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/plans", response_model=list[PaymentPlanSchema])
async def get_plans():
    return [
        PaymentPlanSchema(
            code=plan.code,
            title=plan.title,
            description=plan.description,
            price=plan.price_stars,
            currency="STARS",
            period=f"{plan.duration_days}_days",
            provider="stars",
            recommended=plan.is_most_popular,
        )
        for plan in SUBSCRIPTION_PLANS
    ]


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    payload: SubscribeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    plan = get_plan(payload.plan_code)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    provider = "stars"

    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    subscription = Subscription(
        user_id=user.id,
        provider=provider,
        plan_code=plan.code,
        status=SubscriptionStatus.PENDING,
        is_auto_renew=False,
        started_at=datetime.utcnow(),
    )
    session.add(subscription)
    await session.flush()

    confirmation: dict | None = None
    try:
        await send_stars_invoice_for_subscription(
            bot,
            telegram_id,
            plan_code=plan.code,
            price_rub=plan.price_stars,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Invoice creation failed") from exc
    confirmation = {"provider": "stars", "status": "invoice_sent"}

    # Immediate activation (no webhook for Stars in this flow)
    await ensure_premium_for_user(session, user, plan.code)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.valid_until = datetime.utcnow() + timedelta(days=plan.duration_days)
    user.access_status = AccessStatus.SUBSCRIPTION_ACTIVE

    await log_event(
        session,
        user.id,
        "subscription_started",
        {"plan_code": plan.code, "provider": provider},
    )
    await session.commit()

    return SubscribeResponse(
        subscription_id=subscription.id,
        provider=provider,
        status=subscription.status.value,
        confirmation=confirmation,
    )
