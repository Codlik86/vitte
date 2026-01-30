"""
Telegram messaging utilities for notifications
"""
import httpx
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def send_telegram_notification(
    chat_id: int,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
    bot_token: Optional[str] = None,
) -> Optional[int]:
    """
    Send a notification message to Telegram user.

    Args:
        chat_id: Telegram user ID
        text: Message text
        reply_markup: Optional inline keyboard markup
        bot_token: Optional bot token (if not provided, reads from env)

    Returns:
        Message ID if sent successfully, None otherwise
    """
    token = bot_token or os.getenv("BOT_TOKEN")

    if not token:
        logger.error("BOT_TOKEN not configured, cannot send notification")
        return None

    telegram_api_url = f"https://api.telegram.org/bot{token}"

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": False,
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{telegram_api_url}/sendMessage",
                json=data,
                timeout=10.0
            )

            result = response.json()

            if result.get("ok"):
                message_id = result.get("result", {}).get("message_id")
                logger.info(f"Notification sent to {chat_id}, message_id={message_id}")
                return message_id
            else:
                logger.error(f"Failed to send notification: {result.get('description')}")
                return None

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending notification: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending notification: {e}")
        return None
