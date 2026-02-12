"""
Telegram Service - send messages via Bot API

Uses httpx to send messages to Telegram users directly from API service.
"""

import httpx
import logging
from typing import Optional, Dict, Any

from app.config import config

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{config.bot_token}"

# Default greeting image URL (served via nginx from MinIO)
DEFAULT_GREETING_IMAGE = "https://craveme.tech/storage/universal_pic.jpeg"


def create_refresh_keyboard(dialog_id: int, message_id: int) -> Dict[str, Any]:
    """
    Create inline keyboard with refresh button for LLM responses.

    Args:
        dialog_id: Dialog ID for context
        message_id: Message ID to store in callback data

    Returns:
        Inline keyboard markup dict
    """
    return {
        "inline_keyboard": [[
            {
                "text": "🔄",
                "callback_data": f"refresh:{dialog_id}:{message_id}"
            }
        ]]
    }


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Send a text message to Telegram user.

    Args:
        chat_id: Telegram user ID
        text: Message text
        parse_mode: HTML or Markdown
        disable_notification: Send silently
        reply_markup: Optional inline keyboard markup

    Returns:
        Message ID if sent successfully, None otherwise
    """
    if not config.bot_token:
        logger.error("BOT_TOKEN not configured, cannot send message")
        return None

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json=data,
                timeout=10.0
            )

            result = response.json()

            if result.get("ok"):
                message_id = result.get("result", {}).get("message_id")
                logger.info(f"Sent message to {chat_id}, message_id={message_id}")
                return message_id
            else:
                logger.error(f"Failed to send message: {result.get('description')}")
                return None

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending message: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return None


async def send_photo(
    chat_id: int,
    photo_url: str,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
) -> bool:
    """
    Send a photo to Telegram user.

    Args:
        chat_id: Telegram user ID
        photo_url: URL of the photo to send
        caption: Optional caption text
        parse_mode: HTML or Markdown
        disable_notification: Send silently

    Returns:
        True if sent successfully, False otherwise
    """
    if not config.bot_token:
        logger.error("BOT_TOKEN not configured, cannot send photo")
        return False

    data = {
        "chat_id": chat_id,
        "photo": photo_url,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }

    if caption:
        data["caption"] = caption

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendPhoto",
                json=data,
                timeout=15.0
            )

            result = response.json()

            if result.get("ok"):
                logger.info(f"Sent photo to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo: {result.get('description')}")
                return False

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending photo: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending photo: {e}")
        return False


async def send_photo_bytes(
    chat_id: int,
    photo_bytes: bytes,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
    filename: str = "photo.png",
) -> bool:
    """Send photo as bytes (multipart upload) to Telegram."""
    if not config.bot_token:
        return False

    data = {
        "chat_id": str(chat_id),
        "parse_mode": parse_mode,
    }
    if caption:
        data["caption"] = caption

    files = {"photo": (filename, photo_bytes, "image/png")}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendPhoto",
                data=data,
                files=files,
                timeout=15.0,
            )
            result = response.json()
            if result.get("ok"):
                logger.info(f"Sent photo bytes to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo bytes: {result.get('description')}")
                return False
    except Exception as e:
        logger.error(f"Error sending photo bytes: {e}")
        return False


async def send_greeting(
    chat_id: int,
    persona_name: str,
    greeting_text: str,
    persona_key: Optional[str] = None,
    story_key: Optional[str] = None,
    greeting_image_index: int = 0,
) -> bool:
    """
    Send greeting message from persona to user with image.
    Uses cycling images from MinIO pool when persona_key and story_key are provided.
    """
    from shared.llm.services.greeting_images import get_greeting_image_url

    # Try to get image from greeting pool
    photo_sent = False
    if persona_key and story_key:
        minio_url = get_greeting_image_url(persona_key, story_key, greeting_image_index)
        if minio_url:
            try:
                async with httpx.AsyncClient() as client:
                    img_resp = await client.get(minio_url, timeout=10.0)
                    if img_resp.status_code == 200:
                        # Send photo first, then text separately
                        photo_sent = await send_photo_bytes(chat_id, img_resp.content)
                    else:
                        logger.error(f"Failed to download greeting image: HTTP {img_resp.status_code} from {minio_url}")
            except Exception as e:
                logger.error(f"Error downloading greeting image: {e}")

    # Send text message (always)
    caption = f"💬 <b>{persona_name}</b>\n\n{greeting_text}"

    if not photo_sent:
        # Fallback: send with default image URL
        return await send_photo(chat_id, DEFAULT_GREETING_IMAGE, caption)

    # Photo already sent, send text separately
    await send_message(chat_id, caption)
    return True


async def send_chat_action(
    chat_id: int,
    action: str = "typing",
) -> bool:
    """
    Send chat action (typing indicator) to Telegram.

    Args:
        chat_id: Telegram user ID
        action: Action type (typing, upload_photo, etc.)

    Returns:
        True if sent successfully
    """
    if not config.bot_token:
        logger.error("BOT_TOKEN not configured, cannot send chat action")
        return False

    data = {
        "chat_id": chat_id,
        "action": action,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendChatAction",
                json=data,
                timeout=10.0
            )

            result = response.json()

            if result.get("ok"):
                return True
            else:
                logger.error(f"Failed to send chat action: {result.get('description')}")
                return False

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending chat action: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending chat action: {e}")
        return False
