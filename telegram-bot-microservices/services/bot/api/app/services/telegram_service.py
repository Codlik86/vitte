"""
Telegram Service - send messages via Bot API

Uses httpx to send messages to Telegram users directly from API service.
"""

import httpx
import logging
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{config.bot_token}"


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
) -> bool:
    """
    Send a text message to Telegram user.

    Args:
        chat_id: Telegram user ID
        text: Message text
        parse_mode: HTML or Markdown
        disable_notification: Send silently

    Returns:
        True if sent successfully, False otherwise
    """
    if not config.bot_token:
        logger.error("BOT_TOKEN not configured, cannot send message")
        return False

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json=data,
                timeout=10.0
            )

            result = response.json()

            if result.get("ok"):
                logger.info(f"Sent message to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {result.get('description')}")
                return False

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending message: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        return False


async def send_greeting(
    chat_id: int,
    persona_name: str,
    greeting_text: str,
) -> bool:
    """
    Send greeting message from persona to user.

    Args:
        chat_id: Telegram user ID
        persona_name: Name of the persona
        greeting_text: Generated greeting text

    Returns:
        True if sent successfully
    """
    # Format message with persona context
    message = f"💬 <b>{persona_name}</b>\n\n{greeting_text}"

    return await send_message(chat_id, message)


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
