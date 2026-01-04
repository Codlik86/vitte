from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.store import SUBSCRIPTION_PLANS, IMAGE_PACKS, EMOTIONAL_FEATURES, get_plan, get_image_pack, get_feature
from ..services.subscriptions import ensure_premium_for_user
from ..services.image_quota import get_image_quota, _ensure_balance
from ..services.features import unlock_feature, collect_feature_states
from ..services.telegram_id import get_or_raise_telegram_id
from ..users_service import get_or_create_user_by_telegram_id
from ..services.access import build_access_status, get_active_subscription
from ..logging_config import logger
from ..bot import bot
from ..services.stars import send_stars_invoice_for_subscription, send_stars_invoice_for_feature, create_invoice_link
from ..services.analytics import log_event
from ..models import Purchase, PurchaseStatus, AccessStatus
from ..schemas import StoreBuyRequest, StoreBuyResponse

router = APIRouter(prefix="/api/store", tags=["store"])


@router.get("/config")
async def store_config():
    return {
        "subscription_plans": [plan.__dict__ for plan in SUBSCRIPTION_PLANS],
        "image_packs": [pack.__dict__ for pack in IMAGE_PACKS],
        "emotional_features": [feat.__dict__ for feat in EMOTIONAL_FEATURES],
    }


@router.get("/status")
async def store_status(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, allow_debug=True)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    access = await build_access_status(session, user)
    subscription = await get_active_subscription(session, user.id)
    has_subscription = bool(access.get("has_subscription"))
    quota = access.get("images") or await get_image_quota(session, user, has_subscription=has_subscription)
    features = await collect_feature_states(session, user)
    if os.getenv("DEBUG_LIMITS") == "1":
        logger.info(
            "store_status debug telegram_id=%s has_subscription=%s access_status=%s quota=%s subscription=%s",
            telegram_id,
            has_subscription,
            access.get("access_status"),
            quota,
            subscription.plan_code if subscription else None,
        )
    return {
        "has_active_subscription": has_subscription,
        "subscription_ends_at": subscription.valid_until if subscription else None,
        "remaining_images_today": (quota.get("remaining_free_today") or 0) + (quota.get("remaining_paid") or 0),
        "remaining_paid_images": quota.get("remaining_paid") or 0,
        "unlocked_features": [code for code, state in features.items() if state.unlocked],
        "is_free_user": not has_subscription,
    }


@router.post("/buy/subscription/{plan_code}", response_model=StoreBuyResponse)
async def buy_subscription(
    plan_code: str,
    payload: StoreBuyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    plan = get_plan(plan_code)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    try:
        invoice_url = await create_invoice_link(
            bot,
            title="Подписка Vitte",
            description="Безлимитные сообщения + 20 изображений в день.",
            payload=f"sub:{plan.code}",
            price_stars=plan.price_stars,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create stars invoice link for plan %s: %s", plan.code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    await log_event(session, user.id, "subscription_invoice_sent", {"plan_code": plan.code})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=plan.code, features=None, invoice_url=invoice_url)


@router.post("/buy/image_pack/{pack_code}", response_model=StoreBuyResponse)
async def buy_image_pack(
    pack_code: str,
    payload: StoreBuyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    pack = get_image_pack(pack_code)
    if pack is None:
        raise HTTPException(status_code=404, detail="Image pack not found")
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    try:
        invoice_url = await create_invoice_link(
            bot,
            title="Пакет изображений",
            description=f"{pack.images} изображений",
            payload=f"pack:{pack.code}",
            price_stars=pack.price_stars,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create stars invoice link for pack %s: %s", pack.code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    await log_event(session, user.id, "image_pack_invoice_sent", {"pack": pack.code, "images": pack.images})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=pack.code, features=None, invoice_url=invoice_url)


@router.post("/buy/feature/{feature_code}", response_model=StoreBuyResponse)
async def buy_feature(
    feature_code: str,
    payload: StoreBuyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    feature = get_feature(feature_code)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    try:
        invoice_url = await create_invoice_link(
            bot,
            title=feature.title,
            description=feature.description,
            payload=f"feat:{feature.code}",
            price_stars=feature.price_stars,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create stars invoice link for feature %s: %s", feature.code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    await log_event(session, user.id, "feature_invoice_sent", {"feature": feature.code})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=feature.code, features=[feature.code], invoice_url=invoice_url)
