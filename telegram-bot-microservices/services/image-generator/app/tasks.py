"""
Celery tasks for image generation
"""
import asyncio
from typing import Optional

from celery import Celery
from app.config import config
from app.comfyui_client import ComfyUIClient
from app.comfyui_pool import comfyui_pool
from app.workflow_mapping import get_workflow_path, is_persona_supported
from app.telegram_sender import send_photo_to_telegram
from shared.utils import get_logger

logger = get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "image_generator",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=config.GENERATION_TIMEOUT + 30,  # Kill after timeout + buffer
    worker_prefetch_multiplier=1,  # Take one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after N tasks (prevent memory leaks)
)


@celery_app.task(name="image_generator.generate_and_send")
def generate_and_send_image(
    persona_key: str,
    user_id: int,
    chat_id: int,
    prompt: str,
    seed: Optional[int] = None
) -> dict:
    """
    Generate NSFW image and send to Telegram.

    Args:
        persona_key: Persona identifier (lina, julie, ash, etc.)
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        prompt: Image generation prompt
        seed: Random seed (optional)

    Returns:
        dict with status and result info
    """
    try:
        logger.info(f"Starting image generation for persona={persona_key}, user={user_id}, chat={chat_id}")

        # Validate persona
        if not is_persona_supported(persona_key):
            error_msg = f"Persona '{persona_key}' not supported"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Get workflow path
        workflow_path = get_workflow_path(persona_key)
        if not workflow_path:
            error_msg = f"Workflow not found for persona '{persona_key}'"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Get ComfyUI URL from pool (worker affinity)
        comfyui_url = comfyui_pool.get_comfyui_url()
        logger.info(f"Using ComfyUI instance: {comfyui_url}")

        # Create client for this worker's assigned ComfyUI instance
        client = ComfyUIClient(base_url=comfyui_url)

        # Generate image (async)
        # Create new event loop for Celery worker (get_event_loop doesn't work in threads)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            image_data = loop.run_until_complete(
                client.generate_image(workflow_path, prompt, seed)
            )

            if not image_data:
                error_msg = "Image generation failed"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

            logger.info(f"Image generated successfully, size: {len(image_data)} bytes")

            # Send to Telegram
            success = loop.run_until_complete(
                send_photo_to_telegram(chat_id, image_data)
            )
        finally:
            loop.close()

        if not success:
            error_msg = "Failed to send image to Telegram"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        logger.info(f"Image sent successfully to chat {chat_id}")
        return {
            "success": True,
            "persona": persona_key,
            "user_id": user_id,
            "chat_id": chat_id,
            "image_size": len(image_data)
        }

    except Exception as e:
        error_msg = f"Error in generate_and_send_image: {e}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="image_generator.generate_image")
def generate_image(
    persona_key: str,
    prompt: str,
    seed: Optional[int] = None
) -> dict:
    """
    Generate NSFW image and return URL (don't send to Telegram).

    Args:
        persona_key: Persona identifier (lina, julie, ash, etc.)
        prompt: Image generation prompt
        seed: Random seed (optional)

    Returns:
        dict with success status and image_url
    """
    try:
        logger.info(f"Generating image for persona={persona_key}")

        # Validate persona
        if not is_persona_supported(persona_key):
            error_msg = f"Persona '{persona_key}' not supported"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Get workflow path
        workflow_path = get_workflow_path(persona_key)
        if not workflow_path:
            error_msg = f"Workflow not found for persona '{persona_key}'"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Get ComfyUI URL from pool (worker affinity)
        comfyui_url = comfyui_pool.get_comfyui_url()
        logger.info(f"Using ComfyUI instance: {comfyui_url}")

        # Create client for this worker's assigned ComfyUI instance
        client = ComfyUIClient(base_url=comfyui_url)

        # Generate image (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            image_data = loop.run_until_complete(
                client.generate_image(workflow_path, prompt, seed)
            )

            if not image_data:
                error_msg = "Image generation failed"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

            logger.info(f"Image generated successfully, size: {len(image_data)} bytes")

            # Upload to MinIO and get public URL
            from app.storage import upload_generated_image
            image_url = loop.run_until_complete(
                upload_generated_image(persona_key, image_data)
            )
        finally:
            loop.close()

        if not image_url:
            error_msg = "Failed to upload image to storage"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        logger.info(f"Image uploaded successfully: {image_url}")
        return {
            "success": True,
            "image_url": image_url,
            "persona": persona_key,
            "size_bytes": len(image_data)
        }

    except Exception as e:
        error_msg = f"Error in generate_image: {e}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": str(e)}


@celery_app.task(name="image_generator.health_check")
def health_check() -> dict:
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "service": "image-generator",
        "comfyui_urls": config.COMFYUI_URLS,
        "pool_size": len(config.COMFYUI_URLS)
    }
