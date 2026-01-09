"""
Celery application configuration
"""
from celery import Celery
from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)

# Create Celery app
celery_app = Celery(
    "vitte_worker",
    broker=config.celery_broker_url,
    backend=config.celery_result_backend
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=config.celery_task_time_limit,
    task_soft_time_limit=config.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])

logger.info("Celery app configured")
