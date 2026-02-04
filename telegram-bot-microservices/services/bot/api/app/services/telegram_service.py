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


async def send_greeting(
    chat_id: int,
    persona_name: str,
    greeting_text: str,
    image_url: Optional[str] = None,
) -> bool:
    """
    Send greeting message from persona to user with image.

    Args:
        chat_id: Telegram user ID
        persona_name: Name of the persona
        greeting_text: Generated greeting text
        image_url: Optional custom image URL (defaults to universal_pic)

    Returns:
        True if sent successfully
    """
    # Format caption with persona context
    caption = f"💬 <b>{persona_name}</b>\n\n{greeting_text}"

    # Use default image if not specified
    photo_url = image_url or DEFAULT_GREETING_IMAGE

    return await send_photo(chat_id, photo_url, caption)


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
