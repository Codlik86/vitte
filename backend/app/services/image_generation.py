from __future__ import annotations

from ..services.image_quota import consume_image
from ..models import User, Persona
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_character_image(
    session: AsyncSession,
    user: User,
    persona: Persona,
    prompt: str,
) -> str:
    """
    Stub for future image generation.
    Consumes image quota and returns placeholder URL.
    """
    # TODO: determine subscription flag from access state if needed by caller
    await consume_image(session, user, count=1, has_subscription=False)
    # TODO: replace with actual SD/Lora generation
    return "IMAGE_GENERATION_STUB"
