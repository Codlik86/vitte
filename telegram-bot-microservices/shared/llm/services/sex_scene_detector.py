"""
Sex scene detector — определяет тип контента из диалога через LLM.

Возвращает три уровня:
- pose name (str) — активный половой акт (→ пул фоток)
- "nude" — раздевание/нюдс (→ ComfyUI Moody)
- None — обычный контент (→ ComfyUI ZIT)
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

DETECTION_SYSTEM_PROMPT = """Ты анализатор контента в ролевом чате. Определи тип текущей сцены из диалога.

Варианты ответа:
- missionary — миссионерская позиция (лицом к лицу, мужчина сверху)
- doggy — догги-стайл (на четвереньках, сзади)
- cowgirl — наездница (девушка сверху, лицом к мужчине)
- reverse_cowgirl — обратная наездница (девушка сверху, спиной к мужчине)
- standing_behind — стоя сзади (стоя, мужчина сзади)
- prone_bone — лёжа на животе (девушка на животе, мужчина сверху)
- mating_press — мэтинг-пресс (ноги девушки подняты/прижаты, мужчина сверху)
- arched_doggy — прогнутый догги (на четвереньках с сильным прогибом в спине)
- reverse_lean — откинувшись назад (девушка откинулась назад, опираясь на руки)
- nude — раздевание, нюдс, оголение тела (но без проникновения)
- none — флирт, романтика, поцелуи, объятия, обычный разговор

ПРАВИЛА:
1. Верни ТОЛЬКО одно слово
2. Верни позу ТОЛЬКО если в тексте явно описывается проникновение или активный половой акт (трахает, входит, двигается внутри, ритм, кончает и т.п.)
3. Верни nude если: раздевается, снимает одежду, оголяет грудь/тело, описывается голое тело, стриптиз, прелюдия с обнажением, ласки голого тела
4. Если активный половой акт идёт, но поза не ясна — верни missionary
5. Анализируй ТОЛЬКО последние сообщения"""


async def detect_sex_scene(
    recent_messages: list[dict],
    llm_client,
) -> Optional[str]:
    """
    Определяет тип контента из последних сообщений диалога.

    Args:
        recent_messages: Последние 2-4 сообщения [{role, content}, ...]
        llm_client: LLM клиент для запроса

    Returns:
        - Название позы (str) если активный секс → пул фоток
        - "nude" если раздевание/нюдс → ComfyUI Moody
        - None если обычный контент → ComfyUI ZIT
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
        {"role": "user", "content": f"Диалог:\n{context}\n\nТип сцены?"},
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
        word = result.strip().lower().split()[0].strip(".,!?\"'")

        if word == "none":
            return None

        if word == "nude":
            return "nude"

        if word in VALID_POSES:
            return word

        # Если LLM вернула что-то близкое но не точное — ищем совпадение
        for valid_pose in VALID_POSES:
            if valid_pose in result.lower():
                return valid_pose

        if "nude" in result.lower():
            return "nude"

        logger.warning(f"Sex scene detector returned unknown result: {result}")
        return None

    except Exception as e:
        logger.warning(f"Sex scene detection error: {e}")
        return None
