"""
CryptoPay webhook and payment routes
"""

import logging
import redis.asyncio as aioredis
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from shared.database import get_db
from shared.database.models import User, Subscription, ImageBalance, FeatureUnlock, Purchase
from shared.services import CryptoPayService
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crypto-pay", tags=["cryptopay"])


def get_cryptopay_service() -> CryptoPayService:
    """Dependency to get CryptoPay service instance"""
    return CryptoPayService(api_token=config.cryptopay_token)


@router.post("/webhook")
async def cryptopay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cryptopay: CryptoPayService = Depends(get_cryptopay_service),
):
    """
    CryptoPay webhook endpoint.
    Receives notifications about paid invoices.
    Verifies HMAC-SHA-256 signature from crypto-pay-api-signature header.
    """
    try:
        # Read raw body for signature verification
        body_raw = await request.body()
        update_data = await request.json()

        logger.info(f"Received CryptoPay webhook: {update_data}")

        # Verify webhook signature
        signature = request.headers.get("crypto-pay-api-signature", "")
        if not cryptopay.verify_webhook_signature(body_raw, signature):
            logger.warning(f"Invalid CryptoPay webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse payment data
        payment_info = cryptopay.parse_webhook_update(update_data)

        if not payment_info:
            logger.warning("Invalid or non-payment webhook update")
            return {"ok": True}  # 200 to acknowledge receipt

        # Extract payload: "sub:plus_30d:12345" or "images:pack_20:12345"
        payload = payment_info.get("payload", "")
        parts = payload.split(":")

        if len(parts) != 3:
            logger.error(f"Invalid payload format: {payload}")
            return {"ok": False, "error": "Invalid payload format"}

        action_type, item_id, user_id_str = parts
        user_id = int(user_id_str)

        # Get user
        user = await db.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {"ok": False, "error": "User not found"}

        # Create purchase record
        purchase = Purchase(
            user_id=user_id,
            product_code=item_id,
            provider="cryptopay",
            status="success",
            amount=payment_info["amount"],
            currency="USDT",
            meta={
                "invoice_id": payment_info["invoice_id"],
                "asset": payment_info["asset"],
                "paid_amount": payment_info["paid_amount"],
                "paid_asset": payment_info["paid_asset"],
                "tx_id": payment_info["tx_id"],
                "paid_at": payment_info["paid_at"],
            },
        )
        db.add(purchase)

        # Process based on action type
        if action_type == "sub":
            await _process_subscription_payment(db, user, item_id)
        elif action_type == "images":
            await _process_image_pack_payment(db, user, item_id)
        elif action_type == "upgrade":
            await _process_feature_unlock_payment(db, user, item_id)
        else:
            logger.error(f"Unknown action type: {action_type}")
            return {"ok": False, "error": "Unknown action type"}

        await db.commit()

        # Invalidate Redis caches
        await _invalidate_caches(user_id, action_type)

        logger.info(f"Successfully processed CryptoPay payment for user {user_id}")
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CryptoPay webhook: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


async def _invalidate_caches(user_id: int, action_type: str):
    """Invalidate Redis caches after payment"""
    try:
        redis = aioredis.from_url(config.redis_url)
        if action_type == "sub":
            await redis.delete(f"subscription:{user_id}")
        elif action_type == "upgrade":
            await redis.delete(f"user:{user_id}:features")
        await redis.aclose()
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")


async def _process_subscription_payment(
    db: AsyncSession,
    user: User,
    plan_code: str,
):
    """Process subscription payment"""
    plan_durations = {
        "plus_7d": 7,
        "vitte_plus_7d": 7,
        "plus_30d": 30,
        "vitte_plus_30d": 30,
        "plus_365d": 365,
        "vitte_plus_365d": 365,
    }

    days = plan_durations.get(plan_code)
    if not days:
        logger.error(f"Unknown plan code: {plan_code}")
        return

    now = datetime.now(timezone.utc)

    # Find subscription by user_id (NOT by PK)
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        subscription = Subscription(
            user_id=user.id,
            plan="premium",
            is_active=True,
            started_at=now,
            expires_at=now + timedelta(days=days),
        )
        db.add(subscription)
    else:
        # Extend existing subscription
        if subscription.expires_at and subscription.expires_at > now:
            subscription.expires_at = subscription.expires_at + timedelta(days=days)
        else:
            subscription.expires_at = now + timedelta(days=days)

        subscription.is_active = True
        subscription.plan = "premium"
        subscription.started_at = now

    # Update image balance daily quota
    result = await db.execute(
        select(ImageBalance).where(ImageBalance.user_id == user.id)
    )
    image_balance = result.scalar_one_or_none()

    if not image_balance:
        image_balance = ImageBalance(
            user_id=user.id,
            daily_subscription_quota=20,
            daily_subscription_used=0,
            daily_quota_date=now,
        )
        db.add(image_balance)
    else:
        image_balance.daily_subscription_quota = 20
        image_balance.daily_subscription_used = 0
        image_balance.daily_quota_date = now

    # Update user access status
    user.access_status = "subscription_active"

    logger.info(f"Activated {days}-day subscription for user {user.id}")


async def _process_image_pack_payment(
    db: AsyncSession,
    user: User,
    pack_code: str,
):
    """Process image pack payment"""
    pack_sizes = {
        "pack_10": 10,
        "images_pack_10": 10,
        "pack_20": 20,
        "images_pack_20": 20,
        "pack_30": 30,
        "images_pack_30": 30,
        "pack_50": 50,
        "images_pack_50": 50,
        "pack_100": 100,
        "images_pack_100": 100,
        "pack_200": 200,
        "images_pack_200": 200,
    }

    image_count = pack_sizes.get(pack_code)
    if not image_count:
        logger.error(f"Unknown pack code: {pack_code}")
        return

    # Find image balance by user_id
    result = await db.execute(
        select(ImageBalance).where(ImageBalance.user_id == user.id)
    )
    image_balance = result.scalar_one_or_none()

    if not image_balance:
        image_balance = ImageBalance(
            user_id=user.id,
            total_purchased_images=image_count,
            remaining_purchased_images=image_count,
        )
        db.add(image_balance)
    else:
        image_balance.total_purchased_images += image_count
        image_balance.remaining_purchased_images += image_count

    logger.info(f"Added {image_count} images to user {user.id}")


async def _process_feature_unlock_payment(
    db: AsyncSession,
    user: User,
    feature_code: str,
):
    """Process feature unlock payment"""
    # Find existing feature unlock
    result = await db.execute(
        select(FeatureUnlock).where(
            FeatureUnlock.user_id == user.id,
            FeatureUnlock.feature_code == feature_code,
        )
    )
    feature = result.scalar_one_or_none()

    if not feature:
        feature = FeatureUnlock(
            user_id=user.id,
            feature_code=feature_code,
            enabled=True,
        )
        db.add(feature)
    else:
        feature.enabled = True

    # Update subscription for legacy support
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription and feature_code == "intense_mode":
        subscription.intense_mode = True

    logger.info(f"Unlocked feature {feature_code} for user {user.id}")
