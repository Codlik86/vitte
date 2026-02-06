"""
Image Generation Service
Manages triggering of NSFW image generation via ComfyUI
"""

import logging
import random
from typing import Optional
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Service for triggering image generation."""

    def __init__(self, celery_app):
        """
        Initialize image generation service.

        Args:
            celery_app: Celery app instance for sending tasks
        """
        self.celery_app = celery_app
        self.min_frequency = 3  # Minimum messages before generation
        self.max_frequency = 5  # Maximum messages before generation

    def should_generate_image(self, message_count: int, last_generation_at: Optional[int] = None) -> bool:
        """
        Determine if image should be generated based on message count.

        Args:
            message_count: Current message count in dialog (counts both user and assistant messages)
            last_generation_at: Message count when last image was generated

        Returns:
            True if image should be generated
        """
        # Skip if message_count is 0 or None
        if not message_count or message_count == 0:
            return False

        # message_count counts both user and assistant messages
        # So divide by 2 to get number of user messages (dialog turns)
        user_messages = message_count // 2

        # If no previous generation - generate between 3rd-5th user message
        if last_generation_at is None:
            # Generate on first occurrence in range 3-5
            return user_messages >= self.min_frequency and user_messages <= self.max_frequency

        # Calculate user messages since last generation
        user_messages_since_last = (message_count - last_generation_at) // 2

        # Generate on first occurrence in range 3-5 after last generation
        return user_messages_since_last >= self.min_frequency and user_messages_since_last <= self.max_frequency

    def trigger_generation(
        self,
        persona_key: str,
        user_id: int,
        chat_id: int,
        prompt: str,
        seed: Optional[int] = None
    ) -> Optional[str]:
        """
        Trigger image generation task (async, don't wait).

        Args:
            persona_key: Persona identifier (lina, julie, ash, etc.)
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            prompt: Generation prompt (user message or default)
            seed: Random seed (optional)

        Returns:
            Task ID if successful, None otherwise
        """
        try:
            # Send task to image-generator Celery queue
            task = self.celery_app.send_task(
                'image_generator.generate_and_send',
                args=[persona_key, user_id, chat_id, prompt, seed],
                queue='celery',  # Default queue
            )

            logger.info(
                f"Triggered image generation for persona={persona_key}, "
                f"user={user_id}, chat={chat_id}, task_id={task.id}"
            )

            return task.id

        except Exception as e:
            logger.error(f"Failed to trigger image generation: {e}", exc_info=True)
            return None

    def generate_and_wait(
        self,
        persona_key: str,
        user_id: int,
        chat_id: int,
        prompt: str,
        seed: Optional[int] = None,
        timeout: int = 25
    ) -> Optional[str]:
        """
        Generate image synchronously and wait for result.

        Args:
            persona_key: Persona identifier (lina, julie, ash, etc.)
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            prompt: Generation prompt (user message or default)
            seed: Random seed (optional)
            timeout: Max wait time in seconds (default: 30)

        Returns:
            Image URL if successful, None otherwise
        """
        try:
            # Send task to image-generator service
            task = self.celery_app.send_task(
                'image_generator.generate_image',
                args=[persona_key, prompt, seed],
                queue='celery',
            )

            logger.info(
                f"Waiting for image generation: persona={persona_key}, "
                f"user={user_id}, task_id={task.id}, timeout={timeout}s"
            )

            # Use AsyncResult directly with task_id to retrieve result
            # This avoids NotRegistered error since we don't need task definition
            async_result = AsyncResult(task.id, app=self.celery_app)

            # Wait for task to complete (blocking)
            # propagate=False prevents raising exceptions from task
            result = async_result.get(timeout=timeout, propagate=False)

            if result and isinstance(result, dict) and result.get('success'):
                image_url = result.get('image_url')
                logger.info(
                    f"Image generated successfully: {image_url}, "
                    f"size={result.get('size_bytes', 0)} bytes"
                )
                return image_url
            else:
                error = result.get('error', 'Unknown error') if isinstance(result, dict) and result else 'No result'
                logger.error(f"Image generation failed: {error}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate image: {e}", exc_info=True)
            return None


# Module-level function for easy import (async version - don't wait)
def trigger_image_generation_if_needed(
    celery_app,
    message_count: int,
    persona_key: str,
    user_id: int,
    chat_id: int,
    user_message: str,
    last_generation_at: Optional[int] = None,
) -> Optional[str]:
    """
    Check if image generation should be triggered and trigger if needed (async).

    Args:
        celery_app: Celery app instance
        message_count: Current message count
        persona_key: Persona identifier
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        user_message: User's message (used as prompt)
        last_generation_at: Message count when last image was generated

    Returns:
        Task ID if generation triggered, None otherwise
    """
    service = ImageGenerationService(celery_app)

    if service.should_generate_image(message_count, last_generation_at):
        # Use user message as prompt (will be improved later with prompt builder)
        return service.trigger_generation(
            persona_key=persona_key,
            user_id=user_id,
            chat_id=chat_id,
            prompt=user_message,
            seed=None,  # Random seed
        )

    return None


# Module-level function for synchronous generation (wait for result)
def generate_image_if_needed(
    celery_app,
    message_count: int,
    persona_key: str,
    user_id: int,
    chat_id: int,
    user_message: str,
    last_generation_at: Optional[int] = None,
    timeout: int = 30,
) -> Optional[str]:
    """
    Check if image generation should be triggered and generate synchronously.

    Args:
        celery_app: Celery app instance
        message_count: Current message count
        persona_key: Persona identifier
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        user_message: User's message (used as prompt)
        last_generation_at: Message count when last image was generated
        timeout: Max wait time in seconds (default: 30)

    Returns:
        Image URL if generation triggered and successful, None otherwise
    """
    service = ImageGenerationService(celery_app)

    if service.should_generate_image(message_count, last_generation_at):
        # Use user message as prompt (will be improved later with prompt builder)
        return service.generate_and_wait(
            persona_key=persona_key,
            user_id=user_id,
            chat_id=chat_id,
            prompt=user_message,
            seed=None,  # Random seed
            timeout=timeout,
        )

    return None


__all__ = [
    "ImageGenerationService",
    "trigger_image_generation_if_needed",
    "generate_image_if_needed",
]
