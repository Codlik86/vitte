"""
API Client - call internal API service from bot

Used for generating greetings when user returns to dialog.
"""

import httpx
import logging
from typing import Optional
from dataclasses import dataclass

from app.config import config

logger = logging.getLogger(__name__)


@dataclass
class GreetingResult:
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    dialog_id: Optional[int] = None


@dataclass
class ChatResult:
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    dialog_id: Optional[int] = None
    is_safety_block: bool = False
    message_count: int = 0
    image_url: Optional[str] = None  # URL сгенерированного изображения
    no_image_quota: bool = False  # True when image was due but user has no quota


async def generate_greeting(
    telegram_id: int,
    persona_id: int,
    story_id: Optional[str] = None,
    atmosphere: Optional[str] = None,
    is_return: bool = False,
    send_to_telegram: bool = True,
) -> GreetingResult:
    """
    Call API to generate greeting from persona.

    Args:
        telegram_id: User's Telegram ID
        persona_id: Persona ID
        story_id: Story/scenario ID
        atmosphere: Atmosphere setting
        is_return: Is this a return to existing dialog?
        send_to_telegram: Should API send message to Telegram?

    Returns:
        GreetingResult with response
    """
    url = f"{config.api_url}/api/chat/greeting"

    data = {
        "telegram_id": telegram_id,
        "persona_id": persona_id,
        "is_return": is_return,
        "send_to_telegram": send_to_telegram,
    }

    if story_id:
        data["story_id"] = story_id
    if atmosphere:
        data["atmosphere"] = atmosphere

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=30.0)

            if response.status_code == 200:
                result = response.json()
                return GreetingResult(
                    success=result.get("success", False),
                    response=result.get("response"),
                    error=result.get("error"),
                    dialog_id=result.get("dialog_id"),
                )
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return GreetingResult(
                    success=False,
                    error=f"API error: {response.status_code}",
                )

    except httpx.RequestError as e:
        logger.error(f"HTTP error calling API: {e}")
        return GreetingResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error calling API: {e}")
        return GreetingResult(success=False, error=str(e))


async def send_chat_message(
    telegram_id: int,
    message: str,
    persona_id: Optional[int] = None,
    mode: str = "default",
    story_id: Optional[str] = None,
    atmosphere: Optional[str] = None,
) -> ChatResult:
    """
    Send chat message to API and get persona response.

    Args:
        telegram_id: User's Telegram ID
        message: User's message text
        persona_id: Optional persona ID (uses active dialog if not specified)
        mode: Chat mode
        story_id: Story/scenario ID
        atmosphere: Atmosphere setting

    Returns:
        ChatResult with persona's response
    """
    url = f"{config.api_url}/api/chat"

    data = {
        "telegram_id": telegram_id,
        "message": message,
        "mode": mode,
    }

    if persona_id:
        data["persona_id"] = persona_id
    if story_id:
        data["story_id"] = story_id
    if atmosphere:
        data["atmosphere"] = atmosphere

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=60.0)

            if response.status_code == 200:
                result = response.json()
                return ChatResult(
                    success=result.get("success", False),
                    response=result.get("response"),
                    error=result.get("error"),
                    dialog_id=result.get("dialog_id"),
                    is_safety_block=result.get("is_safety_block", False),
                    message_count=result.get("message_count", 0),
                    image_url=result.get("image_url"),  # Parse image URL from API
                    no_image_quota=result.get("no_image_quota", False),
                )
            else:
                logger.error(f"Chat API error {response.status_code}: {response.text}")
                return ChatResult(
                    success=False,
                    error=f"API error: {response.status_code}",
                )

    except httpx.RequestError as e:
        logger.error(f"HTTP error calling chat API: {e}")
        return ChatResult(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error calling chat API: {e}")
        return ChatResult(success=False, error=str(e))
