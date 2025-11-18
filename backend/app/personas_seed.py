from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Persona


DEFAULT_PERSONAS = [
    {
        "name": "Нежная",
        "short_description": "Тёплый, поддерживающий собеседник",
        "archetype": "gentle",
    },
    {
        "name": "Дерзкая",
        "short_description": "Ироничный, слегка дерзкий флирт",
        "archetype": "sassy",
    },
    {
        "name": "Умная",
        "short_description": "Рациональная, чуть отстранённая, но заботливая",
        "archetype": "smart_cool",
    },
    {
        "name": "Хаотичная",
        "short_description": "Спонтанная, немного безбашенная",
        "archetype": "chaotic",
    },
    {
        "name": "Терапевтичная",
        "short_description": "Мягкая поддержка, рефлексия, вопросы",
        "archetype": "therapeutic",
    },
    {
        "name": "Аниме",
        "short_description": "Аниме-вайб, эмоции, чуть цундере",
        "archetype": "anime",
    },
]


def build_system_prompt(archetype: str, short_description: str) -> str:
    return (
        f"Ты романтический AI-компаньон в стиле {archetype}. "
        f"Говоришь по-русски, мягко, с флиртом, без NSFW-картинок. "
        f"Вайб: {short_description}."
    )


async def ensure_default_personas(session: AsyncSession):
    result = await session.execute(select(Persona).where(Persona.is_default.is_(True)))
    existing = result.scalars().first()
    if existing:
        return

    for p in DEFAULT_PERSONAS:
        persona = Persona(
            name=p["name"],
            short_description=p["short_description"],
            archetype=p["archetype"],
            system_prompt=build_system_prompt(p["archetype"], p["short_description"]),
            long_description=None,
            is_default=True,
            is_custom=False,
            is_active=True,
            owner_user_id=None,
        )
        session.add(persona)

    await session.commit()
