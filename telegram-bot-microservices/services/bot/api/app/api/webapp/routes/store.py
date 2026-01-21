"""
Store API routes for webapp
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from shared.database import get_db, User, Subscription, ImageBalance, FeatureUnlock
from app.services.invoice_service import (
    create_subscription_invoice,
    create_image_pack_invoice,
    create_feature_invoice,
)

router = APIRouter()


# ==================== STORE CONFIG ====================

# Subscription plans
SUBSCRIPTION_PLANS = [
    {
        "code": "weekly",
        "title": "Неделя",
        "description": "7 дней полного доступа",
        "duration_days": 7,
        "price_stars": 150,
        "is_most_popular": False
    },
    {
        "code": "monthly",
        "title": "Месяц",
        "description": "30 дней полного доступа",
        "duration_days": 30,
        "price_stars": 450,
        "is_most_popular": True
    },
    {
        "code": "yearly",
        "title": "Год",
        "description": "365 дней полного доступа",
        "duration_days": 365,
        "price_stars": 2990,
        "is_most_popular": False
    }
]

# Image packs
IMAGE_PACKS = [
    {"code": "pack_10", "images": 10, "price_stars": 50},
    {"code": "pack_30", "images": 30, "price_stars": 120},
    {"code": "pack_100", "images": 100, "price_stars": 350}
]

# Emotional features
EMOTIONAL_FEATURES = [
    {
        "code": "intense_mode",
        "title": "Интенсивный режим",
        "description": "Более эмоциональные и глубокие ответы персонажей",
        "price_stars": 200
    },
    {
        "code": "fantasy_scenes",
        "title": "Фантазийные сцены",
        "description": "Разблокирует расширенные сценарии и истории",
        "price_stars": 200
    }
]


# ==================== SCHEMAS ====================

class SubscriptionPlan(BaseModel):
    code: str
    title: str
    description: str
    duration_days: int
    price_stars: int
    is_most_popular: bool


class ImagePack(BaseModel):
    code: str
    images: int
    price_stars: int


class EmotionalFeature(BaseModel):
    code: str
    title: str
    description: str
    price_stars: int


class StoreConfigResponse(BaseModel):
    subscription_plans: list[SubscriptionPlan]
    image_packs: list[ImagePack]
    emotional_features: list[EmotionalFeature]


class StoreStatusResponse(BaseModel):
    has_active_subscription: bool
    subscription_ends_at: Optional[datetime] = None
    remaining_images_today: int
    remaining_paid_images: int
    unlocked_features: list[str]
    is_free_user: bool


class BuyResponse(BaseModel):
    success: bool
    invoice_url: Optional[str] = None
    message: Optional[str] = None


# ==================== ROUTES ====================

@router.get("/store/config", response_model=StoreConfigResponse)
async def get_store_config():
    """Get store configuration (plans, packs, features)"""
    return StoreConfigResponse(
        subscription_plans=[SubscriptionPlan(**p) for p in SUBSCRIPTION_PLANS],
        image_packs=[ImagePack(**p) for p in IMAGE_PACKS],
        emotional_features=[EmotionalFeature(**f) for f in EMOTIONAL_FEATURES]
    )


@router.get("/store/status", response_model=StoreStatusResponse)
async def get_store_status(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get user's store status (subscription, images, features)"""
    # Get user with relationships
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.subscription),
            selectinload(User.image_balance),
            selectinload(User.feature_unlocks)
        )
        .where(User.id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return StoreStatusResponse(
            has_active_subscription=False,
            subscription_ends_at=None,
            remaining_images_today=0,
            remaining_paid_images=0,
            unlocked_features=[],
            is_free_user=True
        )

    # Check subscription
    subscription = user.subscription
    has_subscription = bool(subscription and subscription.is_active and subscription.expires_at and subscription.expires_at > datetime.utcnow())

    # Get image balance
    image_balance = user.image_balance
    remaining_today = 0
    remaining_paid = 0
    if image_balance:
        remaining_today = max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used)
        remaining_paid = image_balance.remaining_purchased_images

    # Get unlocked features
    unlocked_features = []
    if user.feature_unlocks:
        unlocked_features = [f.feature_code for f in user.feature_unlocks if f.enabled]

    return StoreStatusResponse(
        has_active_subscription=has_subscription,
        subscription_ends_at=subscription.expires_at if subscription else None,
        remaining_images_today=remaining_today,
        remaining_paid_images=remaining_paid,
        unlocked_features=unlocked_features,
        is_free_user=not has_subscription
    )


@router.post("/store/buy/subscription/{plan_code}", response_model=BuyResponse)
async def buy_subscription(
    plan_code: str,
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Initiate subscription purchase"""
    # Validate plan
    plan = next((p for p in SUBSCRIPTION_PLANS if p["code"] == plan_code), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Create Telegram Stars invoice
    invoice_url = await create_subscription_invoice(
        plan_code=plan_code,
        plan_name=plan["title"],
        duration_days=plan["duration_days"],
        price_stars=plan["price_stars"],
        user_id=telegram_id,
    )

    if not invoice_url:
        return BuyResponse(
            success=False,
            invoice_url=None,
            message="Failed to create invoice"
        )

    return BuyResponse(
        success=True,
        invoice_url=invoice_url,
        message=f"Invoice created for plan: {plan['title']}"
    )


@router.post("/store/buy/image_pack/{pack_code}", response_model=BuyResponse)
async def buy_image_pack(
    pack_code: str,
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Initiate image pack purchase"""
    # Validate pack
    pack = next((p for p in IMAGE_PACKS if p["code"] == pack_code), None)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")

    # Create Telegram Stars invoice
    invoice_url = await create_image_pack_invoice(
        pack_code=pack_code,
        images_count=pack["images"],
        price_stars=pack["price_stars"],
        user_id=telegram_id,
    )

    if not invoice_url:
        return BuyResponse(
            success=False,
            invoice_url=None,
            message="Failed to create invoice"
        )

    return BuyResponse(
        success=True,
        invoice_url=invoice_url,
        message=f"Invoice created for {pack['images']} images"
    )


@router.post("/store/buy/feature/{feature_code}", response_model=BuyResponse)
async def buy_feature(
    feature_code: str,
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Initiate feature purchase"""
    # Validate feature
    feature = next((f for f in EMOTIONAL_FEATURES if f["code"] == feature_code), None)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    # Create Telegram Stars invoice
    invoice_url = await create_feature_invoice(
        feature_code=feature_code,
        feature_title=feature["title"],
        feature_description=feature["description"],
        price_stars=feature["price_stars"],
        user_id=telegram_id,
    )

    if not invoice_url:
        return BuyResponse(
            success=False,
            invoice_url=None,
            message="Failed to create invoice"
        )

    return BuyResponse(
        success=True,
        invoice_url=invoice_url,
        message=f"Invoice created for: {feature['title']}"
    )
