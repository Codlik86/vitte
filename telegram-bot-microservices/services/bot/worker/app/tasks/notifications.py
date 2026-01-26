"""
Notification tasks for user and admin alerts
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, and_
import sys
import os

from app.celery_app import celery_app
from shared.database import AsyncSessionLocal, User, Subscription
from shared.utils import get_logger

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../api"))

logger = get_logger(__name__)


async def _get_expiring_subscriptions_async(days_before: int = 3) -> List[Dict[str, Any]]:
    """
    Get subscriptions expiring in N days

    Args:
        days_before: Number of days before expiration

    Returns:
        List of subscriptions that will expire soon
    """
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()
            target_date = now + timedelta(days=days_before)

            # Find active subscriptions expiring within N days
            result = await db.execute(
                select(Subscription, User).join(
                    User, Subscription.user_id == User.id
                ).where(
                    and_(
                        Subscription.is_active == True,
                        Subscription.expires_at.isnot(None),
                        Subscription.expires_at <= target_date,
                        Subscription.expires_at > now
                    )
                )
            )

            expiring = []
            for subscription, user in result:
                expiring.append({
                    "user_id": user.id,
                    "username": user.username,
                    "plan": subscription.plan,
                    "expires_at": subscription.expires_at.isoformat(),
                    "days_left": (subscription.expires_at - now).days
                })

            return expiring

        except Exception as e:
            logger.error(f"Failed to get expiring subscriptions: {e}", exc_info=True)
            raise


async def _send_subscription_expiry_reminder_async(days_before: int = 3) -> Dict[str, Any]:
    """
    Async implementation: send subscription expiry reminders

    Args:
        days_before: Send reminder N days before expiration

    Returns:
        Dict with notification statistics
    """
    try:
        expiring = await _get_expiring_subscriptions_async(days_before)

        # TODO: Implement actual notification sending
        # For now, just log the users who should receive notifications
        # In future: integrate with Telegram bot to send actual messages

        notifications_sent = 0
        for sub in expiring:
            logger.info(
                f"Would send expiry reminder to user {sub['user_id']} "
                f"(plan: {sub['plan']}, expires: {sub['expires_at']})",
                extra=sub
            )
            notifications_sent += 1

        result = {
            "status": "success",
            "notifications_sent": notifications_sent,
            "days_before": days_before,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(
            f"Expiry reminders processed: {notifications_sent} users notified",
            extra=result
        )

        return result

    except Exception as e:
        logger.error(f"Expiry reminder task failed: {e}", exc_info=True)
        raise


async def _send_admin_alert_async(
    alert_type: str,
    message: str,
    severity: str = "info",
    extra_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Async implementation: send alert to admin

    Args:
        alert_type: Type of alert (e.g., "system", "user", "subscription")
        message: Alert message
        severity: Alert severity ("info", "warning", "critical")
        extra_data: Additional data to include

    Returns:
        Dict with alert status
    """
    try:
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "extra_data": extra_data or {}
        }

        # TODO: Implement actual admin notification
        # For now, just log the alert
        # In future: send to admin Telegram, email, or monitoring system

        logger_method = getattr(logger, severity if severity != "critical" else "error")
        logger_method(
            f"Admin alert [{alert_type}]: {message}",
            extra=alert
        )

        return {
            "status": "success",
            "alert_sent": True,
            "alert": alert
        }

    except Exception as e:
        logger.error(f"Admin alert failed: {e}", exc_info=True)
        raise


@celery_app.task(name="notifications.subscription_expiry_reminder", bind=True, max_retries=3)
def send_subscription_expiry_reminder(self, days_before: int = 3):
    """
    Send reminders for expiring subscriptions (Celery task wrapper)

    Args:
        days_before: Send reminder N days before expiration (default: 3)

    Returns:
        Dict with notification statistics
    """
    try:
        logger.info(f"Starting expiry reminder task: days_before={days_before}")
        result = asyncio.run(_send_subscription_expiry_reminder_async(days_before))
        return result
    except Exception as e:
        logger.error(f"Expiry reminder task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="notifications.admin_alert", bind=True, max_retries=3)
def send_admin_alert(
    self,
    alert_type: str,
    message: str,
    severity: str = "info",
    extra_data: Dict[str, Any] = None
):
    """
    Send alert to admin (Celery task wrapper)

    Args:
        alert_type: Type of alert (e.g., "system", "user", "subscription")
        message: Alert message
        severity: Alert severity ("info", "warning", "critical")
        extra_data: Additional data to include

    Returns:
        Dict with alert status
    """
    try:
        logger.info(f"Sending admin alert: type={alert_type}, severity={severity}")
        result = asyncio.run(_send_admin_alert_async(alert_type, message, severity, extra_data))
        return result
    except Exception as e:
        logger.error(f"Admin alert task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _send_dialog_notifications_async() -> Dict[str, Any]:
    """
    Async implementation: check inactive dialogs and send notifications

    Проверяет неактивные диалоги и отправляет уведомления по таймлайну:
    - 20 минут: приветливое
    - 2 часа: чуть грустное
    - 24 часа: грустит без юзера

    Returns:
        Dict with notification statistics
    """
    try:
        from app.services.notification_service import check_and_send_notifications

        async with AsyncSessionLocal() as db:
            sent_count = await check_and_send_notifications(db)

            result = {
                "status": "success",
                "notifications_sent": sent_count,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Dialog notifications processed: {sent_count} notifications sent",
                extra=result
            )

            return result

    except Exception as e:
        logger.error(f"Dialog notification task failed: {e}", exc_info=True)
        raise


@celery_app.task(name="notifications.check_inactive_dialogs", bind=True, max_retries=3)
def check_inactive_dialogs(self):
    """
    Проверить неактивные диалоги и отправить уведомления (Celery task wrapper)

    Запускается по расписанию каждые 10 минут.
    Отправляет уведомления пользователям которые давно не писали в диалог.

    Returns:
        Dict with notification statistics
    """
    try:
        logger.info("Starting inactive dialogs check task")
        result = asyncio.run(_send_dialog_notifications_async())
        return result
    except Exception as e:
        logger.error(f"Inactive dialogs check failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
