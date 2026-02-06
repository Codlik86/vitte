"""
Configuration for Image Generator Service
"""
import os
from pathlib import Path
from urllib.parse import quote_plus


class Config:
    """Image Generator service configuration"""

    # Service
    SERVICE_NAME = "image-generator"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # ComfyUI
    COMFYUI_HOST = os.getenv("COMFYUI_HOST", "195.209.210.175")
    COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8188"))
    COMFYUI_BASE_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

    # Workflows directory
    BASE_DIR = Path(__file__).parent.parent
    WORKFLOWS_DIR = BASE_DIR / "workflows"

    # Redis/Celery
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # Dedicated Redis DBs for image-generator (isolated from worker/beat)
    # Worker/Beat use: DB 0 (general), DB 1 (broker), DB 2 (results)
    # Image-generator uses: DB 3 (broker), DB 4 (results)
    REDIS_BROKER_DB = int(os.getenv("REDIS_BROKER_DB", "3"))
    REDIS_RESULT_DB = int(os.getenv("REDIS_RESULT_DB", "4"))

    # Build Redis URL with password if provided
    if REDIS_PASSWORD:
        # URL-encode password to handle special characters like ! and #
        encoded_password = quote_plus(REDIS_PASSWORD)
        CELERY_BROKER_URL = f"redis://:{encoded_password}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB}"
        CELERY_RESULT_BACKEND = f"redis://:{encoded_password}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULT_DB}"
    else:
        CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB}"
        CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULT_DB}"

    # Bot API (for sending images back to Telegram)
    BOT_API_URL = os.getenv("BOT_API_URL", "http://bot:8000")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # Image Generation Settings
    IMAGE_GENERATION_FREQUENCY = int(os.getenv("IMAGE_GENERATION_FREQUENCY", "4"))  # Every N messages
    MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "2"))  # Parallel generations
    GENERATION_TIMEOUT = int(os.getenv("GENERATION_TIMEOUT", "120"))  # seconds


config = Config()
