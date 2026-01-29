"""
Celery client utilities for admin panel
"""
import os
from datetime import datetime
from typing import Optional
from celery import Celery

from shared.utils import get_logger

logger = get_logger(__name__)

# Celery app configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery_app = Celery(
    "vitte_admin",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)


async def schedule_broadcast_task(broadcast_id: int, scheduled_at: Optional[datetime] = None) -> str:
    """
    Запланировать Celery задачу для выполнения рассылки

    Args:
        broadcast_id: ID рассылки
        scheduled_at: Время запуска (если None - запустить сразу)

    Returns:
        ID задачи Celery
    """
    try:
        if scheduled_at:
            # Запланировать на определенное время
            task = celery_app.send_task(
                "broadcast.execute_scheduled_broadcast",
                args=[broadcast_id],
                eta=scheduled_at
            )
        else:
            # Запустить сразу
            task = celery_app.send_task(
                "broadcast.execute_scheduled_broadcast",
                args=[broadcast_id]
            )

        logger.info(f"Scheduled broadcast task {task.id} for broadcast {broadcast_id}")
        return task.id

    except Exception as e:
        logger.error(f"Failed to schedule broadcast task: {e}")
        raise


async def cancel_broadcast_task(task_id: str) -> bool:
    """
    Отменить Celery задачу

    Args:
        task_id: ID задачи Celery

    Returns:
        True если успешно отменено
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled broadcast task {task_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to cancel broadcast task: {e}")
        return False


async def get_task_status(task_id: str) -> dict:
    """
    Получить статус Celery задачи

    Args:
        task_id: ID задачи Celery

    Returns:
        Словарь со статусом задачи
    """
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None,
        }

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "error": str(e)
        }
