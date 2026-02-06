"""
Celery client for API service
Used to send tasks to worker queues (including image generation)
"""
import os
from celery import Celery

from shared.utils import get_logger

logger = get_logger(__name__)

# Celery app configuration (connects to worker broker)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery_app = Celery(
    "vitte_api",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

logger.info(f"Celery client initialized: broker={CELERY_BROKER_URL}")


__all__ = ["celery_app"]
