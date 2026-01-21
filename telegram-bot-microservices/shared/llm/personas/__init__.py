"""
Все персонажи Vitte Bot

Доступные персонажи:
- Лина (lina) - Озорная фитоняшка
- Марианна (marianna) - Доминантная соседка
- Мей (mei) - Застенчивая, но смелая
- Стейси (stacey) - Игривая романтичная
- Юна (yuna) - Нежная послушная
- Тая (taya) - Похотливая MILF
- Джули (julie) - Неопытная студентка
- Эш (ash) - Фетишистка
"""

from .lina import LINA_METADATA, LINA_BASE_PROMPT, LINA_STORIES
from .marianna import MARIANNA_METADATA, MARIANNA_BASE_PROMPT, MARIANNA_STORIES
from .mei import MEI_METADATA, MEI_BASE_PROMPT, MEI_STORIES
from .stacey import STACEY_METADATA, STACEY_BASE_PROMPT, STACEY_STORIES
from .yuna import YUNA_METADATA, YUNA_BASE_PROMPT, YUNA_STORIES
from .taya import TAYA_METADATA, TAYA_BASE_PROMPT, TAYA_STORIES
from .julie import JULIE_METADATA, JULIE_BASE_PROMPT, JULIE_STORIES
from .ash import ASH_METADATA, ASH_BASE_PROMPT, ASH_STORIES

# Словарь всех персонажей для быстрого доступа по ключу
PERSONAS = {
    "lina": {
        "metadata": LINA_METADATA,
        "base_prompt": LINA_BASE_PROMPT,
        "stories": LINA_STORIES,
    },
    "marianna": {
        "metadata": MARIANNA_METADATA,
        "base_prompt": MARIANNA_BASE_PROMPT,
        "stories": MARIANNA_STORIES,
    },
    "mei": {
        "metadata": MEI_METADATA,
        "base_prompt": MEI_BASE_PROMPT,
        "stories": MEI_STORIES,
    },
    "stacey": {
        "metadata": STACEY_METADATA,
        "base_prompt": STACEY_BASE_PROMPT,
        "stories": STACEY_STORIES,
    },
    "yuna": {
        "metadata": YUNA_METADATA,
        "base_prompt": YUNA_BASE_PROMPT,
        "stories": YUNA_STORIES,
    },
    "taya": {
        "metadata": TAYA_METADATA,
        "base_prompt": TAYA_BASE_PROMPT,
        "stories": TAYA_STORIES,
    },
    "julie": {
        "metadata": JULIE_METADATA,
        "base_prompt": JULIE_BASE_PROMPT,
        "stories": JULIE_STORIES,
    },
    "ash": {
        "metadata": ASH_METADATA,
        "base_prompt": ASH_BASE_PROMPT,
        "stories": ASH_STORIES,
    },
}


def get_persona(key: str) -> dict:
    """
    Получить данные персонажа по ключу.

    Args:
        key: Ключ персонажа (lina, marianna, mei, stacey, yuna, taya, julie, ash)

    Returns:
        dict с metadata, base_prompt и stories

    Raises:
        KeyError: если персонаж не найден
    """
    if key not in PERSONAS:
        raise KeyError(f"Персонаж '{key}' не найден. Доступные: {list(PERSONAS.keys())}")
    return PERSONAS[key]


def get_all_persona_keys() -> list:
    """Получить список всех ключей персонажей."""
    return list(PERSONAS.keys())


def get_persona_stories(key: str) -> dict:
    """Получить все истории персонажа по ключу."""
    return get_persona(key)["stories"]


def get_story(persona_key: str, story_key: str) -> dict:
    """
    Получить конкретную историю персонажа.

    Args:
        persona_key: Ключ персонажа
        story_key: Ключ истории

    Returns:
        dict с данными истории
    """
    stories = get_persona_stories(persona_key)
    if story_key not in stories:
        raise KeyError(f"История '{story_key}' не найдена у персонажа '{persona_key}'")
    return stories[story_key]


__all__ = [
    # Лина
    "LINA_METADATA", "LINA_BASE_PROMPT", "LINA_STORIES",
    # Марианна
    "MARIANNA_METADATA", "MARIANNA_BASE_PROMPT", "MARIANNA_STORIES",
    # Мей
    "MEI_METADATA", "MEI_BASE_PROMPT", "MEI_STORIES",
    # Стейси
    "STACEY_METADATA", "STACEY_BASE_PROMPT", "STACEY_STORIES",
    # Юна
    "YUNA_METADATA", "YUNA_BASE_PROMPT", "YUNA_STORIES",
    # Тая
    "TAYA_METADATA", "TAYA_BASE_PROMPT", "TAYA_STORIES",
    # Джули
    "JULIE_METADATA", "JULIE_BASE_PROMPT", "JULIE_STORIES",
    # Эш
    "ASH_METADATA", "ASH_BASE_PROMPT", "ASH_STORIES",
    # Общие
    "PERSONAS",
    "get_persona",
    "get_all_persona_keys",
    "get_persona_stories",
    "get_story",
]
