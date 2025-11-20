from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..db import get_session
from ..integrations.stars_client import create_stars_invoice
from ..integrations.yookassa_client import create_payment, verify_webhook_signature
from ..models import Subscription, SubscriptionStatus, AccessStatus
from ..schemas import PaymentPlanSchema, SubscribeRequest, SubscribeResponse
from ..services.analytics import log_event
from ..services.payments import (
    estimate_valid_until,
    get_payment_plan,
    list_payment_plans,
)
from ..users_service import get_or_create_user_by_telegram_id

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/plans", response_model=list[PaymentPlanSchema])
async def get_plans():
    return [
        PaymentPlanSchema(
            code=plan.code,
            title=plan.title,
            description=plan.description,
            price=plan.price,
            currency=plan.currency,
            period=plan.period,
            provider=plan.provider,
            recommended=plan.recommended,
        )
        for plan in list_payment_plans()
    ]


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    payload: SubscribeRequest,
    session: AsyncSession = Depends(get_session),
):
    plan = get_payment_plan(payload.plan_code)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    provider = payload.provider or plan.provider
    if provider not in {"yookassa", "stars"}:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)

    subscription = Subscription(
        user_id=user.id,
        provider=provider,
        plan_code=plan.code,
        status=SubscriptionStatus.PENDING,
        is_auto_renew=provider == "yookassa",
        started_at=datetime.utcnow(),
    )
    session.add(subscription)
    await session.flush()

    confirmation: dict | None = None
    if provider == "yookassa":
        payment = await create_payment(
            amount=plan.price,
            currency=plan.currency,
            description=plan.title,
            return_url=settings.miniapp_url,
            metadata={
                "subscription_id": subscription.id,
                "plan_code": plan.code,
            },
        )
        subscription.external_payment_id = payment.get("id")
        subscription.confirmation_payload = payment
        confirmation = payment.get("confirmation")
    else:
        invoice = create_stars_invoice(
            user_id=user.id,
            product_code=plan.code,
            amount_stars=plan.price,
            description=plan.description,
            metadata={
                "subscription_id": subscription.id,
                "plan_code": plan.code,
            },
        )
        subscription.confirmation_payload = invoice
        confirmation = invoice

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


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    content_hmac: str | None = Header(default=None, alias="Content-HMAC"),
    session: AsyncSession = Depends(get_session),
):
    body = await request.body()
    if not verify_webhook_signature(body, content_hmac):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    payment_data = payload.get("object") or {}
    payment_id = payment_data.get("id")
    metadata = payment_data.get("metadata") or {}

    stmt = select(Subscription).options(selectinload(Subscription.user))
    if metadata.get("subscription_id"):
        stmt = stmt.where(Subscription.id == metadata["subscription_id"])
    else:
        stmt = stmt.where(Subscription.external_payment_id == payment_id)
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    status = payment_data.get("status")
    if status == "succeeded":
        subscription.status = SubscriptionStatus.ACTIVE
        plan = get_payment_plan(subscription.plan_code)
        if plan:
            subscription.valid_until = estimate_valid_until(plan, subscription.started_at)
        subscription.confirmation_payload = payment_data
        if subscription.user:
            subscription.user.access_status = AccessStatus.SUBSCRIPTION_ACTIVE
            await log_event(
                session,
                subscription.user.id,
                "subscription_renewed",
                {"plan_code": subscription.plan_code, "provider": subscription.provider},
            )
    elif status in {"canceled", "refunded"}:
        subscription.status = SubscriptionStatus.CANCELED
        if subscription.user:
            subscription.user.access_status = AccessStatus.TRIAL_USAGE
            await log_event(
                session,
                subscription.user.id,
                "subscription_canceled",
                {"plan_code": subscription.plan_code},
            )

    await session.commit()
    return {"ok": True}
