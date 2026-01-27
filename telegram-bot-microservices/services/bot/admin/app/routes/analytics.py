"""
Analytics and admin API routes for Grafana dashboards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List

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

    - Доход сегодня
    - Доход за месяц
    - Доход за все время
    """
    try:
        async for db in get_db():
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Revenue today
            revenue_today = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.created_at >= today_start
                )
            )

            # Revenue this month
            revenue_month = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(
                    Purchase.status == 'success',
                    Purchase.created_at >= month_start
                )
            )

            # Revenue all time
            revenue_total = await db.scalar(
                select(func.coalesce(func.sum(Purchase.amount), 0))
                .where(Purchase.status == 'success')
            )

            # Payments count today
            payments_today = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.created_at >= today_start
                )
            )

            # Payments count this month
            payments_month = await db.scalar(
                select(func.count(Purchase.id))
                .where(
                    Purchase.status == 'success',
                    Purchase.created_at >= month_start
                )
            )

            return {
                "revenue_today_stars": int(revenue_today or 0),
                "revenue_month_stars": int(revenue_month or 0),
                "revenue_total_stars": int(revenue_total or 0),
                "payments_today": payments_today or 0,
                "payments_month": payments_month or 0,
                "currency": "XTR"  # Telegram Stars
            }

    except Exception as e:
        logger.error(f"Error getting revenue summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/recent")
async def get_recent_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    telegram_id: Optional[str] = Query(None)
):
    """
    Последние платежи (все транзакции)

    Таблица с полями:
    - transaction_id
    - telegram_id
    - username
    - product_code
    - amount (stars)
    - status
    - provider
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

            # Return flat structure for easier Grafana Infinity plugin parsing
            return {
                # User info (flat)
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language": user.language_code,
                "utm_source": user.utm_source,
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "is_admin": user.is_admin,
                "access_status": user.access_status,
                "free_messages_used": user.free_messages_used,
                "free_messages_limit": user.free_messages_limit,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_interaction": user.last_interaction.isoformat() if user.last_interaction else None,
                # Subscription info (flat)
                "has_subscription": subscription is not None and subscription.is_active,
                "subscription_plan": subscription.plan if subscription else "free",
                "subscription_is_active": subscription.is_active if subscription else False,
                "subscription_started_at": subscription.started_at.isoformat() if subscription and subscription.started_at else None,
                "subscription_expires_at": subscription.expires_at.isoformat() if subscription and subscription.expires_at else None,
                "intense_mode": subscription.intense_mode if subscription else False,
                "fantasy_scenes": subscription.fantasy_scenes if subscription else False,
                # Payments info (flat)
                "payments_total_count": payments.count or 0,
                "payments_total_stars": int(payments.total) if payments.total else 0,
                "first_payment": payments.first.isoformat() if payments.first else None,
                "last_payment": payments.last.isoformat() if payments.last else None,
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

    - Общее количество пользователей
    - Активных за последние 24h
    - Всего диалогов
    - Всего сообщений
    - Среднее сообщений на пользователя
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
                }
            }

    except Exception as e:
        logger.error(f"Error getting technical stats: {e}")
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
