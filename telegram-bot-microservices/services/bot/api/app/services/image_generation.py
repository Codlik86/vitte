"""
Image Generation Service
Manages triggering of NSFW image generation via ComfyUI
"""

import logging
import random
from typing import Optional

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
            message_count: Current message count in dialog
            last_generation_at: Message count when last image was generated

        Returns:
            True if image should be generated
        """
        # Skip if message_count is 0 or None
        if not message_count or message_count == 0:
            return False

        # If no previous generation - use random frequency
        if last_generation_at is None:
            # Random frequency between 3-5 messages
            frequency = random.randint(self.min_frequency, self.max_frequency)
            return message_count >= frequency

        # Calculate messages since last generation
        messages_since_last = message_count - last_generation_at

        # Generate if enough messages passed (random 3-5)
        frequency = random.randint(self.min_frequency, self.max_frequency)
        return messages_since_last >= frequency

    def trigger_generation(
        self,
        persona_key: str,
        user_id: int,
        chat_id: int,
        prompt: str,
        seed: Optional[int] = None
    ) -> Optional[str]:
        """
        Trigger image generation task.

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


# Module-level function for easy import
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
    Check if image generation should be triggered and trigger if needed.

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


__all__ = [
    "ImageGenerationService",
    "trigger_image_generation_if_needed",
]
