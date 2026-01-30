"""
Cleanup tasks for database maintenance
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from shared.database import AsyncSessionLocal, Dialog, Message
from shared.database.services import delete_old_messages
from shared.utils import get_logger

logger = get_logger(__name__)


async def _cleanup_old_messages_async(keep_last: int = 50, days_threshold: int = 30) -> Dict[str, Any]:
    """
    Async implementation: cleanup old messages from database

    Args:
        keep_last: Number of recent messages to keep per dialog
        days_threshold: Delete messages older than N days

    Returns:
        Dict with cleanup statistics
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get all active dialogs
            result = await db.execute(
                select(Dialog).where(Dialog.is_active == True)
            )
            dialogs = result.scalars().all()

            total_deleted = 0
            dialogs_processed = 0

            for dialog in dialogs:
                # Delete old messages, keep last N
                deleted = await delete_old_messages(db, dialog.id, keep_last=keep_last)
                total_deleted += deleted
                dialogs_processed += 1

            await db.commit()

            logger.info(
                f"Cleanup completed: {total_deleted} messages deleted from {dialogs_processed} dialogs",
                extra={"deleted": total_deleted, "dialogs": dialogs_processed}
            )

            return {
                "status": "success",
                "deleted": total_deleted,
                "dialogs_processed": dialogs_processed,
                "keep_last": keep_last,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            raise


async def _cleanup_inactive_dialogs_async(days_inactive: int = 30) -> Dict[str, Any]:
    """
    Async implementation: soft delete dialogs inactive for N days

    Args:
        days_inactive: Mark dialogs as inactive if no updates for N days

    Returns:
        Dict with cleanup statistics
    """
    async with AsyncSessionLocal() as db:
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_inactive)

            # Find dialogs that haven't been updated in N days
            result = await db.execute(
                select(Dialog).where(
                    and_(
                        Dialog.is_active == True,
                        Dialog.updated_at < threshold_date
                    )
                )
            )
            inactive_dialogs = result.scalars().all()

            # Soft delete (mark as inactive)
            archived_count = 0
            for dialog in inactive_dialogs:
                dialog.is_active = False
                archived_count += 1

            await db.commit()

            logger.info(
                f"Archived {archived_count} inactive dialogs (inactive > {days_inactive} days)",
                extra={"archived": archived_count, "threshold_days": days_inactive}
            )

            return {
                "status": "success",
                "archived": archived_count,
                "threshold_days": days_inactive,
                "threshold_date": threshold_date.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Dialog cleanup failed: {e}", exc_info=True)
            raise


@celery_app.task(name="cleanup.old_messages", bind=True, max_retries=3)
def cleanup_old_messages(self, keep_last: int = 50, days_threshold: int = 30):
    """
    Cleanup old messages from database (Celery task wrapper)

    Args:
        keep_last: Number of recent messages to keep per dialog (default: 50)
        days_threshold: Delete messages older than N days (default: 30)

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Starting cleanup: keep_last={keep_last}, days_threshold={days_threshold}")
        result = asyncio.run(_cleanup_old_messages_async(keep_last, days_threshold))
        return result
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="cleanup.inactive_dialogs", bind=True, max_retries=3)
def cleanup_inactive_dialogs(self, days_inactive: int = 30):
    """
    Archive dialogs inactive for N days (Celery task wrapper)

    Args:
        days_inactive: Archive dialogs inactive for N days (default: 30)

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Starting dialog cleanup: days_inactive={days_inactive}")
        result = asyncio.run(_cleanup_inactive_dialogs_async(days_inactive))
        return result
    except Exception as e:
        logger.error(f"Dialog cleanup task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="cleanup.test_task")
def test_task(x: int, y: int):
    """Test task for Celery"""
    logger.info(f"Test task called with x={x}, y={y}")
    result = x + y
    logger.info(f"Test task result: {result}")
    return {"result": result}
