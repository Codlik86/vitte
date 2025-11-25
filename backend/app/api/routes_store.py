from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Query
import json
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..integrations.stars_client import create_stars_invoice
from ..models import Purchase, PurchaseStatus
from ..schemas import (
    StoreProductsResponse,
    StorePurchaseRequest,
    StorePurchaseResponse,
    StoreBuyRequest,
    StoreBuyResponse,
)
from ..services.analytics import log_event
from ..services.features import apply_product_purchase
from ..services.store import get_store_product, list_store_products
from ..users_service import get_or_create_user_by_telegram_id
from ..logging_config import logger
from ..services.telegram_id import get_or_raise_telegram_id
from ..billing.prices import FEATURE_PRICES_STARS
from ..bot import bot, STAR_MULTIPLIER
from aiogram.types import LabeledPrice

router = APIRouter(prefix="/api/store", tags=["store"])


@router.get("/products", response_model=StoreProductsResponse)
async def store_products():
    return {
        "products": [
            {
                "product_code": product.product_code,
                "title": product.title,
                "description": product.description,
                "price_stars": product.price_stars,
                "type": product.type,
            }
            for product in list_store_products()
        ]
    }


@router.post("/purchase", response_model=StorePurchaseResponse)
async def purchase_product(
    payload: StorePurchaseRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    product = get_store_product(payload.product_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    try:
        invoice = create_stars_invoice(
            user_id=user.id,
            product_code=product.product_code,
            amount_stars=product.price_stars,
            description=product.description,
            metadata={"product_code": product.product_code},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create invoice for user %s product %s: %s", user.id, product.product_code, exc)
        raise HTTPException(status_code=502, detail="Invoice creation failed")

    purchase = Purchase(
        user_id=user.id,
        product_code=product.product_code,
        provider="stars",
        amount=product.price_stars,
        currency="STARS",
        status=PurchaseStatus.PENDING,
        meta=invoice,
    )
    session.add(purchase)
    await session.flush()

    await log_event(
        session,
        user.id,
        "purchase_started",
        {"product_code": product.product_code, "provider": "stars"},
    )

    await session.commit()

    return StorePurchaseResponse(
        purchase_id=purchase.id,
        provider=purchase.provider,
        status=purchase.status.value,
        invoice=invoice,
    )


@router.post("/buy/{product_code}", response_model=StoreBuyResponse)
async def buy_product(
    product_code: str,
    payload: StoreBuyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    product = get_store_product(product_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    purchase = Purchase(
        user_id=user.id,
        product_code=product.product_code,
        provider="stars",
        amount=product.price_stars,
        currency="STARS",
        status=PurchaseStatus.SUCCESS,
        meta={"mode": "direct_feature_purchase"},
    )
    session.add(purchase)
    await session.flush()

    try:
        activated_features = apply_product_purchase(user, product.product_code)
    except ValueError:
        logger.error("Feature mapping missing for product %s", product.product_code)
        raise HTTPException(status_code=400, detail="Feature mapping missing")

    event_overrides = {"images": "feature_image_pack_activated"}
    for feature in activated_features:
        event_type = event_overrides.get(feature.code, f"feature_{feature.code}_activated")
        await log_event(
            session,
            user.id,
            event_type,
            {"product_code": product.product_code, "until": feature.until.isoformat() if feature.until else None},
        )

    await session.commit()

    activated_until = None
    if activated_features:
        activated_until = max((item.until for item in activated_features if item.until), default=None)

    return StoreBuyResponse(
        ok=True,
        product_code=product.product_code,
        activated_until=activated_until,
        features=[item.code for item in activated_features],
    )


@router.post("/invoice", response_model=dict)
async def create_feature_invoice(
    request: Request,
    product_code: str = Query(..., description="Feature product code"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request)
    price_stars = FEATURE_PRICES_STARS.get(product_code)
    if price_stars is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    amount_units = price_stars * STAR_MULTIPLIER
    payload = json.dumps({"product_code": f"feature_{product_code}"})
    try:
        link = await bot.create_invoice_link(
            title="Улучшения Vitte",
            description="Оплата улучшения для Vitte",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=product_code, amount=amount_units)],
        )
    except Exception as exc:
        logger.error("Failed to create feature invoice: %s", exc)
        raise HTTPException(status_code=502, detail="Не удалось создать счёт")
    return {"invoice_link": link}
