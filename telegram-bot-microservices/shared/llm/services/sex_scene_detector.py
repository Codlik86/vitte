"""
Sex scene detector — определяет позу из диалога через LLM.

Берёт последние 2-4 сообщения и через мини-запрос к LLM
определяет текущую секс-позу (или отсутствие секс-контекста).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Все доступные позы (совпадают с SCENE_MAP в sex_images.py)
VALID_POSES = {
    "missionary",
    "doggy",
    "cowgirl",
    "reverse_cowgirl",
    "standing_behind",
    "prone_bone",
    "mating_press",
    "arched_doggy",
    "reverse_lean",
}

DETECTION_SYSTEM_PROMPT = """Ты анализатор секс-сцен в ролевом чате. Определи текущую секс-позу из диалога.

Варианты поз:
- missionary — миссионерская позиция (лицом к лицу, мужчина сверху)
- doggy — догги-стайл (на четвереньках, сзади)
- cowgirl — наездница (девушка сверху, лицом к мужчине)
- reverse_cowgirl — обратная наездница (девушка сверху, спиной к мужчине)
- standing_behind — стоя сзади (стоя, мужчина сзади)
- prone_bone — лёжа на животе (девушка на животе, мужчина сверху)
- mating_press — мэтинг-пресс (ноги девушки подняты/прижаты, мужчина сверху)
- arched_doggy — прогнутый догги (на четвереньках с сильным прогибом в спине)
- reverse_lean — откинувшись назад (девушка откинулась назад, опираясь на руки)
- none — секс-сцены нет, обычный разговор

ПРАВИЛА:
1. Верни ТОЛЬКО одно слово — название позы или none
2. Если секс-контекст есть, но поза не ясна, верни missionary (самая частая)
3. Если контекст флирт/прелюдия без конкретного секса, верни none
4. Анализируй ТОЛЬКО последние сообщения"""


async def detect_sex_scene(
    recent_messages: list[dict],
    llm_client,
) -> Optional[str]:
    """
    Определяет секс-позу из последних сообщений диалога.

    Args:
        recent_messages: Последние 2-4 сообщения [{role, content}, ...]
        llm_client: LLM клиент для запроса

    Returns:
        Название позы (str) или None если секс-сцены нет
    """
    if not recent_messages:
        return None

    # Формируем контекст из последних сообщений
    context_parts = []
    for msg in recent_messages[-4:]:
        role = "Девушка" if msg.get("role") == "assistant" else "Мужчина"
        content = msg.get("content", "")[:300]
        context_parts.append(f"{role}: {content}")

    context = "\n".join(context_parts)

    messages = [
        {"role": "system", "content": DETECTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Диалог:\n{context}\n\nКакая поза?"},
    ]

    try:
        result = await llm_client.chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=20,
        )

        if not result:
            return None

        # Парсим ответ — берём первое слово, убираем мусор
        pose = result.strip().lower().split()[0].strip(".,!?\"'")

        if pose == "none":
            return None

        if pose in VALID_POSES:
            return pose

        # Если LLM вернула что-то близкое но не точное
        # Пробуем найти совпадение
        for valid_pose in VALID_POSES:
            if valid_pose in result.lower():
                return valid_pose

        logger.warning(f"Sex scene detector returned unknown pose: {result}")
        return None

    except Exception as e:
        logger.warning(f"Sex scene detection error: {e}")
        return None
