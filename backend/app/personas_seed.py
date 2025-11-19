from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Persona


DEFAULT_PERSONAS = [
    {
        "name": "Лина",
        "short_description": "Тёплая, поддерживающая подруга",
        "archetype": "gentle",
    },
    {
        "name": "Эва",
        "short_description": "Более смелая и флиртующая",
        "archetype": "sassy",
    },
    {
        "name": "Мия",
        "short_description": "Спокойная и рациональная собеседница",
        "archetype": "smart_cool",
    },
    {
        "name": "Фэй",
        "short_description": "Игривый характер с юмором",
        "archetype": "chaotic",
    },
    {
        "name": "Арина",
        "short_description": "Заботливая и мягкая",
        "archetype": "therapeutic",
    },
    {
        "name": "Аки",
        "short_description": "Аниме-вайб, немного дерзкая",
        "archetype": "anime_tsundere",
    },
    {
        "name": "Хана",
        "short_description": "Нежная и мечтательная",
        "archetype": "anime_waifu_soft",
    },
]


def build_system_prompt(archetype: str, short_description: str) -> str:
    return (
        f"Ты романтический AI-компаньон в стиле {archetype}. "
        f"Говоришь по-русски, мягко, с флиртом, без NSFW-картинок. "
        f"Вайб: {short_description}."
    )


async def ensure_default_personas(session: AsyncSession):
    for p in DEFAULT_PERSONAS:
        result = await session.execute(
            select(Persona).where(Persona.name == p["name"], Persona.is_default.is_(True))
        )
        persona = result.scalar_one_or_none()
        if persona:
            persona.short_description = p["short_description"]
            persona.archetype = p["archetype"]
            persona.system_prompt = build_system_prompt(p["archetype"], p["short_description"])
            persona.is_default = True
            persona.is_custom = False
            persona.owner_user_id = None
            persona.is_active = True
        else:
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
