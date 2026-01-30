"""
Main entry point for Celery worker
This file is used to import the celery app
"""
from app.celery_app import celery_app
from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)

logger.info(f"Worker configured in {config.environment} mode")
logger.info(f"Broker: {config.celery_broker_url}")
logger.info(f"Backend: {config.celery_result_backend}")

# Import all tasks to register them
from app.tasks import *

if __name__ == "__main__":
    # This is typically not used since worker is started via:
    # celery -A app.celery_app worker --loglevel=info
    logger.warning("Worker should be started via celery command, not directly")
