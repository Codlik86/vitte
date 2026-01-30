"""
Report generation tasks for admin dashboard
"""
import asyncio
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import select, func, and_

from app.celery_app import celery_app
from shared.database import AsyncSessionLocal, User, Subscription, Dialog, Message
from shared.utils import get_logger

logger = get_logger(__name__)


async def _generate_user_stats_async() -> Dict[str, Any]:
    """
    Async implementation: generate user statistics

    Returns:
        Dict with user statistics
    """
    async with AsyncSessionLocal() as db:
        try:
            # Total users
            total_users_result = await db.execute(
                select(func.count(User.id))
            )
            total_users = total_users_result.scalar() or 0

            # Active users (interacted in last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users_result = await db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.is_active == True,
                        User.last_interaction >= thirty_days_ago
                    )
                )
            )
            active_users = active_users_result.scalar() or 0

            # Blocked users
            blocked_users_result = await db.execute(
                select(func.count(User.id)).where(User.is_blocked == True)
            )
            blocked_users = blocked_users_result.scalar() or 0

            # Admin users
            admin_users_result = await db.execute(
                select(func.count(User.id)).where(User.is_admin == True)
            )
            admin_users = admin_users_result.scalar() or 0

            # Total dialogs
            total_dialogs_result = await db.execute(
                select(func.count(Dialog.id))
            )
            total_dialogs = total_dialogs_result.scalar() or 0

            # Active dialogs
            active_dialogs_result = await db.execute(
                select(func.count(Dialog.id)).where(Dialog.is_active == True)
            )
            active_dialogs = active_dialogs_result.scalar() or 0

            # Total messages
            total_messages_result = await db.execute(
                select(func.count(Message.id))
            )
            total_messages = total_messages_result.scalar() or 0

            stats = {
                "status": "success",
                "users": {
                    "total": total_users,
                    "active_30d": active_users,
                    "blocked": blocked_users,
                    "admins": admin_users,
                },
                "dialogs": {
                    "total": total_dialogs,
                    "active": active_dialogs,
                    "inactive": total_dialogs - active_dialogs,
                },
                "messages": {
                    "total": total_messages,
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"User stats generated: {total_users} users, {active_users} active",
                extra=stats
            )

            return stats

        except Exception as e:
            logger.error(f"User stats generation failed: {e}", exc_info=True)
            raise


async def _generate_subscription_report_async() -> Dict[str, Any]:
    """
    Async implementation: generate subscription statistics

    Returns:
        Dict with subscription statistics
    """
    async with AsyncSessionLocal() as db:
        try:
            # Total subscriptions
            total_subs_result = await db.execute(
                select(func.count(Subscription.id))
            )
            total_subscriptions = total_subs_result.scalar() or 0

            # Active subscriptions
            active_subs_result = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.is_active == True)
            )
            active_subscriptions = active_subs_result.scalar() or 0

            # Free plan
            free_plan_result = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.plan == "free")
            )
            free_plan = free_plan_result.scalar() or 0

            # Premium plan
            premium_plan_result = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.plan == "premium")
            )
            premium_plan = premium_plan_result.scalar() or 0

            # Enterprise plan
            enterprise_plan_result = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.plan == "enterprise")
            )
            enterprise_plan = enterprise_plan_result.scalar() or 0

            # Messages usage stats
            messages_used_result = await db.execute(
                select(func.sum(Subscription.messages_used))
            )
            total_messages_used = messages_used_result.scalar() or 0

            # Images usage stats
            images_used_result = await db.execute(
                select(func.sum(Subscription.images_used))
            )
            total_images_used = images_used_result.scalar() or 0

            # Expiring soon (within 7 days)
            from datetime import timedelta
            seven_days_from_now = datetime.utcnow() + timedelta(days=7)
            expiring_soon_result = await db.execute(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at <= seven_days_from_now,
                        Subscription.expires_at.isnot(None)
                    )
                )
            )
            expiring_soon = expiring_soon_result.scalar() or 0

            report = {
                "status": "success",
                "subscriptions": {
                    "total": total_subscriptions,
                    "active": active_subscriptions,
                    "inactive": total_subscriptions - active_subscriptions,
                },
                "plans": {
                    "free": free_plan,
                    "premium": premium_plan,
                    "enterprise": enterprise_plan,
                },
                "usage": {
                    "messages_used": total_messages_used,
                    "images_used": total_images_used,
                },
                "expiring_soon_7d": expiring_soon,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Subscription report generated: {total_subscriptions} total, {active_subscriptions} active",
                extra=report
            )

            return report

        except Exception as e:
            logger.error(f"Subscription report generation failed: {e}", exc_info=True)
            raise


@celery_app.task(name="reports.user_stats", bind=True, max_retries=3)
def generate_user_stats(self):
    """
    Generate user statistics report (Celery task wrapper)

    Returns:
        Dict with user statistics
    """
    try:
        logger.info("Generating user stats report")
        result = asyncio.run(_generate_user_stats_async())
        return result
    except Exception as e:
        logger.error(f"User stats task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="reports.subscription_report", bind=True, max_retries=3)
def generate_subscription_report(self):
    """
    Generate subscription statistics report (Celery task wrapper)

    Returns:
        Dict with subscription statistics
    """
    try:
        logger.info("Generating subscription report")
        result = asyncio.run(_generate_subscription_report_async())
        return result
    except Exception as e:
        logger.error(f"Subscription report task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
