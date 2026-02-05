"""
Main entry point for Image Generator service
Celery worker for NSFW image generation
"""
from app.tasks import celery_app
from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__, config.LOG_LEVEL)


if __name__ == "__main__":
    logger.info(f"Starting Image Generator service...")
    logger.info(f"ComfyUI URL: {config.COMFYUI_BASE_URL}")
    logger.info(f"Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
    logger.info(f"Max concurrent generations: {config.MAX_CONCURRENT_GENERATIONS}")

    # Start Celery worker
    celery_app.worker_main([
        'worker',
        f'--concurrency={config.MAX_CONCURRENT_GENERATIONS}',
        '--loglevel=INFO',
        f'--hostname=image-generator@%h',
    ])
