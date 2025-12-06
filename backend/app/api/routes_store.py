from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.store import SUBSCRIPTION_PLANS, IMAGE_PACKS, EMOTIONAL_FEATURES, get_plan, get_image_pack, get_feature
from ..services.subscriptions import ensure_premium_for_user
from ..services.image_quota import get_image_quota, _ensure_balance
from ..services.features import unlock_feature, collect_feature_states
from ..services.telegram_id import get_or_raise_telegram_id
from ..users_service import get_or_create_user_by_telegram_id
from ..services.access import get_active_subscription
from ..logging_config import logger
from ..bot import bot
from ..services.stars import send_stars_invoice_for_subscription, send_stars_invoice_for_feature
from ..services.analytics import log_event
from ..models import Purchase, PurchaseStatus
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
    subscription = await get_active_subscription(session, user.id)
    quota = await get_image_quota(session, user, has_subscription=bool(subscription))
    features = await collect_feature_states(session, user)
    return {
        "has_active_subscription": bool(subscription),
        "subscription_ends_at": subscription.valid_until if subscription else None,
        "remaining_images_today": quota["remaining_free_today"] + quota["remaining_paid"],
        "remaining_paid_images": quota["remaining_paid"],
        "unlocked_features": [code for code, state in features.items() if state.unlocked],
        "is_free_user": not bool(subscription),
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

    price_rub = plan.price_stars  # Stars invoice uses rub_to_stars internally
    try:
        await send_stars_invoice_for_subscription(
            bot, telegram_id, plan_code=plan.code, price_rub=price_rub
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send stars invoice for plan %s: %s", plan.code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    # immediate activation (Stars callback отсутствует) — активируем сразу
    await ensure_premium_for_user(session, user, plan.code)
    await log_event(session, user.id, "subscription_activated", {"plan_code": plan.code})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=plan.code, features=None)


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
    purchase = Purchase(
        user_id=user.id,
        product_code=pack.code,
        provider="stars",
        amount=pack.price_stars,
        currency="STARS",
        status=PurchaseStatus.SUCCESS,
        meta={"mode": "image_pack"},
    )
    session.add(purchase)
    await session.flush()
    balance = await _ensure_balance(session, user)
    balance.total_purchased_images += pack.images
    balance.remaining_purchased_images += pack.images
    await log_event(session, user.id, "image_pack_purchased", {"pack": pack.code, "images": pack.images})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=pack.code, features=None)


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

    price_rub = feature.price_stars  # Stars invoice uses rub_to_stars internally
    try:
        await send_stars_invoice_for_feature(
            bot,
            telegram_id,
            feature_code=feature.code,
            title=feature.title,
            description=feature.description,
            price_rub=price_rub,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send stars invoice for feature %s: %s", feature.code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    await unlock_feature(session, user, feature.code)
    await log_event(session, user.id, "feature_unlocked", {"feature": feature.code})
    await session.commit()
    return StoreBuyResponse(ok=True, product_code=feature.code, features=[feature.code])
