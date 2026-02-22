"""
Analytics and admin API routes for Grafana dashboards
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select, func, and_, or_, desc, case, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

from shared.database import (
    User, Subscription, Purchase, Dialog, Message,
    FeatureUnlock, ImageBalance, get_db
)
from shared.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ==================== USER MANAGEMENT ====================

@router.get("/users/all")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    telegram_id: Optional[str] = Query(None),
    utm_source: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Получить всех пользователей с полной информацией

    Столбцы:
    - telegram_id
    - utm_source
    - first_name
    - last_name
    - username
    - language_code
    - created_at (регистрация)
    - payments_count (кол-во платежей)
    - total_stars_spent (потрачено звезд)
    - has_subscription (наличие подписки)
    - has_upgrades (есть ли улучшения)
    """
    try:
        async for db in get_db():
            # Build query
            query = (
                select(
                    User.id.label('telegram_id'),
                    User.utm_source,
                    User.first_name,
                    User.last_name,
                    User.username,
                    User.language_code,
                    User.created_at,
                    User.is_active,
                    User.is_blocked,
                    func.count(Purchase.id).label('payments_count'),
                    func.coalesce(func.sum(Purchase.amount), 0).label('total_stars_spent'),
                    case(
                        (Subscription.is_active == True, True),
                        else_=False
                    ).label('has_subscription'),
                    Subscription.plan.label('subscription_plan'),
                    func.count(FeatureUnlock.id).label('upgrades_count')
                )
                .outerjoin(Purchase, and_(
                    Purchase.user_id == User.id,
                    Purchase.status == 'success'
                ))
                .outerjoin(Subscription, Subscription.user_id == User.id)
                .outerjoin(FeatureUnlock, and_(
                    FeatureUnlock.user_id == User.id,
                    FeatureUnlock.enabled == True
                ))
                .group_by(
                    User.id,
                    User.utm_source,
                    User.first_name,
                    User.last_name,
                    User.username,
                    User.language_code,
                    User.created_at,
                    User.is_active,
                    User.is_blocked,
                    Subscription.is_active,
                    Subscription.plan
                )
                .order_by(desc(User.created_at))
            )

            # Filters
            if telegram_id and telegram_id.strip():
                try:
                    tid = int(telegram_id)
                    query = query.where(User.id == tid)
                except ValueError:
                    pass  # Ignore invalid telegram_id

            if utm_source:
                query = query.where(User.utm_source == utm_source)

            if search:
                query = query.where(
                    or_(
                        User.username.ilike(f'%{search}%'),
                        User.first_name.ilike(f'%{search}%'),
                        User.last_name.ilike(f'%{search}%')
                    )
                )

            # Pagination
            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            users = result.all()

            return {
                "data": [
                    {
                        "telegram_id": u.telegram_id,
                        "utm_source": u.utm_source,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "username": u.username,
                        "language": u.language_code,
                        "registered_at": u.created_at.isoformat() if u.created_at else None,
                        "is_active": u.is_active,
                        "is_blocked": u.is_blocked,
                        "payments_count": u.payments_count,
                        "total_stars_spent": int(u.total_stars_spent),
                        "has_subscription": u.has_subscription,
                        "subscription_plan": u.subscription_plan,
                        "has_upgrades": u.upgrades_count > 0
                    }
                    for u in users
                ],
                "skip": skip,
                "limit": limit
            }

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PAYMENTS & REVENUE ====================

@router.get("/revenue/summary")
async def get_revenue_summary():
    """
    Сводка по доходам

    - Доход сегодня / месяц / всё время по Stars (XTR)
    - Доход сегодня / месяц / всё время по крипте (USDT)
    - Количество платежей
    """
    try:
        async for db in get_db():
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Stars (XTR) revenue
            revenue_today_stars = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'XTR',
                    Purchase.created_at >= today_start
                )
            )
            revenue_month_stars = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'XTR',
                    Purchase.created_at >= month_start
                )
            )
            revenue_total_stars = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(Purchase.status == 'success', Purchase.currency == 'XTR')
            )

            # Crypto (USDT) revenue
            revenue_today_usdt = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'USDT',
                    Purchase.created_at >= today_start
                )
            )
            revenue_month_usdt = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'USDT',
                    Purchase.created_at >= month_start
                )
            )
            revenue_total_usdt = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(Purchase.status == 'success', Purchase.currency == 'USDT')
            )

            # Payments count (Stars)
            payments_today_stars = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'XTR',
                    Purchase.created_at >= today_start
                )
            )
            payments_month_stars = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'XTR',
                    Purchase.created_at >= month_start
                )
            )

            # Payments count (Crypto)
            payments_today_crypto = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'USDT',
                    Purchase.created_at >= today_start
                )
            )
            payments_month_crypto = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.currency == 'USDT',
                    Purchase.created_at >= month_start
                )
            )

            return {
                # Stars
                "revenue_today_stars": int(revenue_today_stars or 0),
                "revenue_month_stars": int(revenue_month_stars or 0),
                "revenue_total_stars": int(revenue_total_stars or 0),
                "payments_today": int(payments_today_stars or 0),
                "payments_month": int(payments_month_stars or 0),
                # Crypto
                "revenue_today_usdt": float(revenue_today_usdt or 0),
                "revenue_month_usdt": float(revenue_month_usdt or 0),
                "revenue_total_usdt": float(revenue_total_usdt or 0),
                "payments_today_crypto": int(payments_today_crypto or 0),
                "payments_month_crypto": int(payments_month_crypto or 0),
                "currency": "XTR"
            }

    except Exception as e:
        logger.error(f"Error getting revenue summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/recent")
async def get_recent_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    telegram_id: Optional[str] = Query(None),
    provider: Optional[str] = Query(None, description="Filter by provider: telegram_stars or cryptopay")
):
    """
    Последние платежи (все транзакции)

    Таблица с полями:
    - transaction_id
    - telegram_id
    - username
    - product_code
    - amount
    - currency (XTR или USDT)
    - status
    - provider (telegram_stars / cryptopay)
    - created_at
    """
    try:
        async for db in get_db():
            query = (
                select(
                    Purchase.id.label('transaction_id'),
                    User.id.label('telegram_id'),
                    User.username,
                    User.first_name,
                    User.last_name,
                    Purchase.product_code,
                    Purchase.amount,
                    Purchase.currency,
                    Purchase.status,
                    Purchase.provider,
                    Purchase.created_at
                )
                .join(User, User.id == Purchase.user_id)
                .order_by(desc(Purchase.created_at))
            )

            if telegram_id and telegram_id.strip():
                try:
                    tid = int(telegram_id)
                    query = query.where(User.id == tid)
                except ValueError:
                    pass

            if provider and provider.strip():
                query = query.where(Purchase.provider == provider.strip())

            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            payments = result.all()

            return {
                "data": [
                    {
                        "transaction_id": p.transaction_id,
                        "telegram_id": p.telegram_id,
                        "username": p.username,
                        "first_name": p.first_name,
                        "last_name": p.last_name,
                        "product_code": p.product_code,
                        "amount": int(p.amount) if p.amount else 0,
                        "currency": p.currency,
                        "status": p.status,
                        "provider": p.provider,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    }
                    for p in payments
                ],
                "skip": skip,
                "limit": limit
            }

    except Exception as e:
        logger.error(f"Error getting recent payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/top-spenders")
async def get_top_spenders(limit: int = Query(50, ge=1, le=100)):
    """
    Топ платящих пользователей

    - telegram_id
    - username
    - total_spent (stars)
    - payments_count
    - first_payment_date
    - last_payment_date
    """
    try:
        async for db in get_db():
            query = (
                select(
                    User.id.label('telegram_id'),
                    User.username,
                    User.first_name,
                    User.last_name,
                    func.sum(Purchase.amount).label('total_spent'),
                    func.count(Purchase.id).label('payments_count'),
                    func.min(Purchase.created_at).label('first_payment_date'),
                    func.max(Purchase.created_at).label('last_payment_date')
                )
                .join(Purchase, Purchase.user_id == User.id)
                .where(Purchase.status == 'success')
                .group_by(User.id, User.username, User.first_name, User.last_name)
                .order_by(desc('total_spent'))
                .limit(limit)
            )

            result = await db.execute(query)
            spenders = result.all()

            return {
                "data": [
                    {
                        "telegram_id": s.telegram_id,
                        "username": s.username,
                        "first_name": s.first_name,
                        "last_name": s.last_name,
                        "total_spent": int(s.total_spent),
                        "payments_count": s.payments_count,
                        "first_payment": s.first_payment_date.isoformat() if s.first_payment_date else None,
                        "last_payment": s.last_payment_date.isoformat() if s.last_payment_date else None
                    }
                    for s in spenders
                ]
            }

    except Exception as e:
        logger.error(f"Error getting top spenders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USER CARD ====================

@router.get("/user/{telegram_id}/card")
async def get_user_card(telegram_id: str):
    """
    Карточка пользователя - вся информация о юзере

    - Основная информация
    - Подписка
    - Статистика платежей
    - Статистика сообщений
    - Активные диалоги
    - Улучшения
    """
    # Validate telegram_id
    if not telegram_id or not telegram_id.strip():
        raise HTTPException(status_code=400, detail="telegram_id is required")

    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id format")

    try:
        async for db in get_db():
            # Get user
            user = await db.scalar(select(User).where(User.id == tid))
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Get subscription
            subscription = await db.scalar(
                select(Subscription).where(Subscription.user_id == tid)
            )

            # Get payments stats
            payments_stats = await db.execute(
                select(
                    func.count(Purchase.id).label('count'),
                    func.sum(Purchase.amount).label('total'),
                    func.min(Purchase.created_at).label('first'),
                    func.max(Purchase.created_at).label('last')
                )
                .where(
                    Purchase.user_id == tid,
                    Purchase.status == 'success'
                )
            )
            payments = payments_stats.one()

            # Get messages stats
            messages_count = await db.scalar(
                select(func.count(Message.id))
                .join(Dialog, Dialog.id == Message.dialog_id)
                .where(Dialog.user_id == tid)
            )

            # Get active dialogs
            active_dialogs = await db.scalar(
                select(func.count(Dialog.id))
                .where(
                    Dialog.user_id == tid,
                    Dialog.is_active == True
                )
            )

            # Get feature unlocks
            unlocks = await db.execute(
                select(FeatureUnlock)
                .where(
                    FeatureUnlock.user_id == tid,
                    FeatureUnlock.enabled == True
                )
            )
            features = [u.feature_code for u in unlocks.scalars().all()]

            # Get image balance
            image_balance = await db.scalar(
                select(ImageBalance).where(ImageBalance.user_id == tid)
            )

            # Return flat structure for Grafana Infinity plugin with UQL parser
            # NOTE: UQL doesn't handle null/boolean well, so convert to strings/defaults
            return {
                # User info (flat) - convert null to empty string for UQL compatibility
                "telegram_id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "language": user.language_code or "",
                "utm_source": user.utm_source or "",
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "is_admin": user.is_admin,
                "access_status": user.access_status or "",
                "free_messages_used": user.free_messages_used,
                "free_messages_limit": user.free_messages_limit,
                "created_at": user.created_at.isoformat() if user.created_at else "",
                "last_interaction": user.last_interaction.isoformat() if user.last_interaction else "",
                # Subscription info (flat) - convert boolean to string for UQL
                "has_subscription": "true" if (subscription is not None and subscription.is_active) else "false",
                "subscription_plan": subscription.plan if subscription else "free",
                "subscription_is_active": subscription.is_active if subscription else False,
                "subscription_started_at": subscription.started_at.isoformat() if subscription and subscription.started_at else "",
                "subscription_expires_at": subscription.expires_at.isoformat() if subscription and subscription.expires_at else "",
                "intense_mode": subscription.intense_mode if subscription else False,
                "fantasy_scenes": subscription.fantasy_scenes if subscription else False,
                # Payments info (flat)
                "payments_total_count": payments.count or 0,
                "payments_total_stars": int(payments.total) if payments.total else 0,
                "first_payment": payments.first.isoformat() if payments.first else "",
                "last_payment": payments.last.isoformat() if payments.last else "",
                # Activity info (flat)
                "messages_count": messages_count or 0,
                "active_dialogs": active_dialogs or 0,
                # Features (array)
                "features_unlocked": features,
                # Images info (flat)
                "images_total_purchased": image_balance.total_purchased_images if image_balance else 0,
                "images_remaining": image_balance.remaining_purchased_images if image_balance else 0,
                "images_daily_quota": image_balance.daily_subscription_quota if image_balance else 0,
                "images_daily_used": image_balance.daily_subscription_used if image_balance else 0
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TECHNICAL METRICS ====================

@router.get("/tech/stats")
async def get_technical_stats():
    """
    Технические метрики системы

    - Общее количество пользователей / активных за 24h
    - Всего диалогов / активных
    - Всего сообщений / среднее на юзера
    - Активных подписок
    - Генерации: диалоги с ComfyUI, диалоги с sex pool
    - Платежи: Stars vs Crypto (кол-во транзакций)
    """
    try:
        async for db in get_db():
            now = datetime.utcnow()
            day_ago = now - timedelta(days=1)

            # Total users
            total_users = await db.scalar(select(func.count(User.id)))

            # Active users (24h)
            active_24h = await db.scalar(
                select(func.count(User.id))
                .where(User.last_interaction >= day_ago)
            )

            # Total dialogs
            total_dialogs = await db.scalar(select(func.count(Dialog.id)))

            # Active dialogs
            active_dialogs = await db.scalar(
                select(func.count(Dialog.id))
                .where(Dialog.is_active == True)
            )

            # Total messages
            total_messages = await db.scalar(select(func.count(Message.id)))

            # Total subscriptions
            total_subs = await db.scalar(
                select(func.count(Subscription.id))
                .where(Subscription.is_active == True)
            )

            # Dialogs that had at least one ComfyUI generation
            dialogs_with_comfyui = await db.scalar(
                select(func.count(Dialog.id))
                .where(Dialog.last_image_generation_at.isnot(None))
            )

            # Dialogs that used sex image pool (sex_scene_indices not empty)
            dialogs_with_sex_pool = await db.scalar(
                select(func.count(Dialog.id))
                .where(
                    Dialog.sex_scene_indices.isnot(None),
                    func.jsonb_typeof(Dialog.sex_scene_indices.cast(type_=None)) == 'object'
                )
            )

            # Payments by provider
            payments_stars_total = await db.scalar(
                select(func.count(Purchase.id))
                .where(Purchase.status == 'success', Purchase.provider == 'telegram_stars')
            )
            payments_crypto_total = await db.scalar(
                select(func.count(Purchase.id))
                .where(Purchase.status == 'success', Purchase.provider == 'cryptopay')
            )
            payments_stars_today = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.provider == 'telegram_stars',
                    Purchase.created_at >= day_ago
                )
            )
            payments_crypto_today = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.provider == 'cryptopay',
                    Purchase.created_at >= day_ago
                )
            )

            return {
                "users": {
                    "total": total_users or 0,
                    "active_24h": active_24h or 0
                },
                "dialogs": {
                    "total": total_dialogs or 0,
                    "active": active_dialogs or 0
                },
                "messages": {
                    "total": total_messages or 0,
                    "avg_per_user": round((total_messages or 0) / (total_users or 1), 2)
                },
                "subscriptions": {
                    "active": total_subs or 0
                },
                "generations": {
                    "dialogs_with_comfyui": dialogs_with_comfyui or 0,
                    "dialogs_with_sex_pool": dialogs_with_sex_pool or 0,
                },
                "payments": {
                    "stars_total": payments_stars_total or 0,
                    "crypto_total": payments_crypto_total or 0,
                    "stars_today": payments_stars_today or 0,
                    "crypto_today": payments_crypto_today or 0,
                }
            }

    except Exception as e:
        logger.error(f"Error getting technical stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== UTM STATS ====================

@router.get("/utm/summary")
async def get_utm_summary():
    """
    Общая статистика по UTM меткам
    - Всего пользователей с UTM
    - Количество уникальных UTM меток
    """
    try:
        async for db in get_db():
            # Total users with UTM
            total_with_utm = await db.scalar(
                select(func.count(User.id))
                .where(User.utm_source.isnot(None), User.utm_source != '')
            )

            # Unique UTM sources count
            unique_utm_count = await db.scalar(
                select(func.count(func.distinct(User.utm_source)))
                .where(User.utm_source.isnot(None), User.utm_source != '')
            )

            return {
                "total_users_with_utm": total_with_utm or 0,
                "unique_utm_sources": unique_utm_count or 0
            }
    except Exception as e:
        logger.error(f"Error getting UTM summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/utm/top")
async def get_top_utm_sources(limit: int = Query(10, ge=1, le=100)):
    """
    Топ UTM меток с метриками
    - utm_source
    - users_count (количество пользователей)
    - payments_count (количество платежей)
    - total_revenue (общая выручка)
    - subscriptions_count (количество подписок)
    """
    try:
        async for db in get_db():
            # Get UTM stats
            query = (
                select(
                    User.utm_source,
                    func.count(func.distinct(User.id)).label('users_count'),
                    func.count(func.distinct(Purchase.id)).label('payments_count'),
                    func.coalesce(func.sum(Purchase.amount), 0).label('total_revenue'),
                    func.count(func.distinct(
                        case((and_(Subscription.is_active == True, Subscription.plan != 'free'), Subscription.id), else_=None)
                    )).label('subscriptions_count')
                )
                .outerjoin(Purchase, and_(Purchase.user_id == User.id, Purchase.status == 'success'))
                .outerjoin(Subscription, Subscription.user_id == User.id)
                .where(User.utm_source.isnot(None), User.utm_source != '')
                .group_by(User.utm_source)
                .order_by(desc('users_count'))
                .limit(limit)
            )

            result = await db.execute(query)
            utm_stats = result.all()

            return {
                "utm_sources": [
                    {
                        "utm_source": row.utm_source,
                        "users_count": row.users_count,
                        "payments_count": row.payments_count,
                        "total_revenue": int(row.total_revenue),
                        "subscriptions_count": row.subscriptions_count
                    }
                    for row in utm_stats
                ]
            }
    except Exception as e:
        logger.error(f"Error getting top UTM sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USER MANAGEMENT ACTIONS ====================

class SubscriptionAction(BaseModel):
    action: str  # grant_premium, revoke
    days: Optional[int] = 30

class ImagesAction(BaseModel):
    action: str  # add, reset
    amount: Optional[int] = 0

class FeaturesAction(BaseModel):
    action: str  # grant, revoke
    feature_code: str


@router.post("/user/{telegram_id}/subscription")
async def manage_user_subscription(telegram_id: str, body: SubscriptionAction):
    """Manage user subscription: grant premium or revoke"""
    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id")

    try:
        async for db in get_db():
            user = await db.get(User, tid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            sub = await db.scalar(
                select(Subscription).where(Subscription.user_id == tid)
            )

            if body.action == "grant_premium":
                now = datetime.utcnow()
                if sub:
                    sub.plan = "premium"
                    sub.is_active = True
                    sub.started_at = now
                    sub.expires_at = now + timedelta(days=body.days or 30)
                else:
                    sub = Subscription(
                        user_id=tid,
                        plan="premium",
                        is_active=True,
                        started_at=now,
                        expires_at=now + timedelta(days=body.days or 30),
                    )
                    db.add(sub)

                user.access_status = "subscription_active"
                await db.commit()
                return {"status": "ok", "message": f"Premium granted for {body.days} days"}

            elif body.action == "revoke":
                if sub:
                    sub.is_active = False
                    sub.plan = "free"
                    sub.expires_at = None
                user.access_status = "trial_usage"
                await db.commit()
                return {"status": "ok", "message": "Subscription revoked"}

            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{telegram_id}/images")
async def manage_user_images(telegram_id: str, body: ImagesAction):
    """Manage user images: add or reset"""
    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id")

    try:
        async for db in get_db():
            user = await db.get(User, tid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            balance = await db.scalar(
                select(ImageBalance).where(ImageBalance.user_id == tid)
            )

            if body.action == "add":
                amount = body.amount or 0
                if balance:
                    balance.total_purchased_images += amount
                    balance.remaining_purchased_images += amount
                else:
                    balance = ImageBalance(
                        user_id=tid,
                        total_purchased_images=amount,
                        remaining_purchased_images=amount,
                    )
                    db.add(balance)
                await db.commit()
                return {"status": "ok", "message": f"Added {amount} images"}

            elif body.action == "reset":
                if balance:
                    balance.total_purchased_images = 0
                    balance.remaining_purchased_images = 0
                    await db.commit()
                return {"status": "ok", "message": "Images reset to 0"}

            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{telegram_id}/features")
async def manage_user_features(telegram_id: str, body: FeaturesAction):
    """Manage user features: grant or revoke"""
    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id")

    try:
        async for db in get_db():
            user = await db.get(User, tid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if body.action == "grant":
                existing = await db.scalar(
                    select(FeatureUnlock).where(
                        FeatureUnlock.user_id == tid,
                        FeatureUnlock.feature_code == body.feature_code
                    )
                )
                if existing:
                    existing.enabled = True
                else:
                    db.add(FeatureUnlock(
                        user_id=tid,
                        feature_code=body.feature_code,
                        enabled=True,
                    ))

                # Also update subscription flags if applicable
                sub = await db.scalar(select(Subscription).where(Subscription.user_id == tid))
                if sub:
                    if body.feature_code == "intense_mode":
                        sub.intense_mode = True
                    elif body.feature_code == "fantasy_scenes":
                        sub.fantasy_scenes = True

                await db.commit()
                return {"status": "ok", "message": f"Feature {body.feature_code} granted"}

            elif body.action == "revoke":
                existing = await db.scalar(
                    select(FeatureUnlock).where(
                        FeatureUnlock.user_id == tid,
                        FeatureUnlock.feature_code == body.feature_code
                    )
                )
                if existing:
                    existing.enabled = False

                sub = await db.scalar(select(Subscription).where(Subscription.user_id == tid))
                if sub:
                    if body.feature_code == "intense_mode":
                        sub.intense_mode = False
                    elif body.feature_code == "fantasy_scenes":
                        sub.fantasy_scenes = False

                await db.commit()
                return {"status": "ok", "message": f"Feature {body.feature_code} revoked"}

            else:
                raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{telegram_id}/activity")
async def get_user_activity(telegram_id: str):
    """Get user activity history: purchases, dialogs, subscriptions"""
    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id")

    try:
        async for db in get_db():
            user = await db.get(User, tid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            activities = []

            # Purchases
            purchases_result = await db.execute(
                select(Purchase)
                .where(Purchase.user_id == tid)
                .order_by(desc(Purchase.created_at))
                .limit(50)
            )
            for p in purchases_result.scalars():
                activities.append({
                    "type": "purchase",
                    "description": p.product_code,
                    "details": f"{p.amount} {p.currency or 'stars'} — {p.status}",
                    "created_at": p.created_at.isoformat() if p.created_at else "",
                })

            # Dialogs
            dialogs_result = await db.execute(
                select(Dialog)
                .where(Dialog.user_id == tid)
                .order_by(desc(Dialog.created_at))
                .limit(50)
            )
            for d in dialogs_result.scalars():
                activities.append({
                    "type": "dialog",
                    "description": d.title or f"Dialog #{d.id}",
                    "details": f"Persona #{d.persona_id}, {d.message_count} msgs",
                    "created_at": d.created_at.isoformat() if d.created_at else "",
                })

            # Feature unlocks
            features_result = await db.execute(
                select(FeatureUnlock)
                .where(FeatureUnlock.user_id == tid)
                .order_by(desc(FeatureUnlock.unlocked_at))
            )
            for f in features_result.scalars():
                activities.append({
                    "type": "feature",
                    "description": f.feature_code,
                    "details": "Enabled" if f.enabled else "Disabled",
                    "created_at": f.unlocked_at.isoformat() if f.unlocked_at else "",
                })

            # Sort by date
            activities.sort(key=lambda x: x["created_at"], reverse=True)

            return activities

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{telegram_id}")
async def delete_user_account(telegram_id: str):
    """Completely delete user account from database"""
    try:
        tid = int(telegram_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_id")

    try:
        async for db in get_db():
            user = await db.get(User, tid)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Delete in order (respect foreign keys)
            # Messages (via dialogs cascade), but be explicit
            dialogs = await db.execute(select(Dialog.id).where(Dialog.user_id == tid))
            dialog_ids = [d[0] for d in dialogs.all()]
            if dialog_ids:
                await db.execute(sa_delete(Message).where(Message.dialog_id.in_(dialog_ids)))

            await db.execute(sa_delete(Dialog).where(Dialog.user_id == tid))
            await db.execute(sa_delete(Purchase).where(Purchase.user_id == tid))
            await db.execute(sa_delete(FeatureUnlock).where(FeatureUnlock.user_id == tid))
            await db.execute(sa_delete(ImageBalance).where(ImageBalance.user_id == tid))
            await db.execute(sa_delete(Subscription).where(Subscription.user_id == tid))

            # Delete user
            await db.delete(user)
            await db.commit()

            # Try to clear Redis cache
            try:
                import redis
                import os
                redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
                r = redis.from_url(redis_url)
                # Delete all keys matching this user
                for key in r.scan_iter(f"*{tid}*"):
                    r.delete(key)
            except Exception as redis_err:
                logger.warning(f"Could not clear Redis cache: {redis_err}")

            return {"status": "ok", "message": f"User {tid} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BROADCAST SERVICE (placeholder) ====================

@router.get("/broadcast/stats")
async def get_broadcast_stats():
    """
    Статистика рассылок (пока пустая, будет реализована позже)
    """
    return {
        "total_broadcasts": 0,
        "pending": 0,
        "sent": 0,
        "failed": 0,
        "message": "Broadcast service not implemented yet"
    }
