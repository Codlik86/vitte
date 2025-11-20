from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..integrations.stars_client import create_stars_invoice
from ..models import Purchase, PurchaseStatus
from ..schemas import StoreProductsResponse, StorePurchaseRequest, StorePurchaseResponse
from ..services.analytics import log_event
from ..services.store import get_store_product, list_store_products
from ..users_service import get_or_create_user_by_telegram_id

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
    session: AsyncSession = Depends(get_session),
):
    product = get_store_product(payload.product_code)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)

    invoice = create_stars_invoice(
        user_id=user.id,
        product_code=product.product_code,
        amount_stars=product.price_stars,
        description=product.description,
        metadata={"product_code": product.product_code},
    )

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
