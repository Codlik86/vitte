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
