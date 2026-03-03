"""
Sex scene detector — определяет тип контента из диалога через LLM.

Возвращает три уровня:
- pose name (str) — активный половой акт (→ пул фоток)
- "nude" — раздевание/нюдс (→ ComfyUI Moody)
- None — обычный контент (→ ComfyUI ZIT)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Паттерны для мгновенного детекта запросов "покажи X" → сразу nude (без LLM)
# Срабатывает на последнем сообщении юзера
_SHOW_NUDE_PATTERN_RU = re.compile(
    r"покажи\s+(свои?\s+)?(сиськ|грудь|письк|киск|вагин|пизд|жоп|поп|попк|ягодиц|анал|дырк|трус|нижн)",
    re.IGNORECASE,
)
_SHOW_NUDE_PATTERN_EN = re.compile(
    r"show\s+(me\s+)?(your\s+)?(boob|tit|breast|pussy|vagina|ass|butt|anus|hole|underwear|panties|naked|nude)",
    re.IGNORECASE,
)

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

DETECTION_SYSTEM_PROMPT_EN = """You are a content analyzer in a roleplay chat. Determine the type of current scene from the dialogue.

Response options:
- missionary — missionary position (face to face, man on top)
- doggy — doggy style (on all fours, from behind)
- cowgirl — cowgirl (girl on top, facing the man)
- reverse_cowgirl — reverse cowgirl (girl on top, facing away from the man)
- standing_behind — standing from behind (standing, man behind)
- prone_bone — prone bone (girl on her stomach, man on top)
- mating_press — mating press (girl's legs raised/pressed up, man on top)
- arched_doggy — arched doggy (on all fours with a strong arch in the back)
- reverse_lean — leaning back (girl leaning back, resting on her hands)
- nude — undressing, nudity, baring the body (but without penetration)
- none — flirting, romance, kissing, hugging, normal conversation

RULES:
1. Return ONLY one word
2. Return a pose ONLY if the text explicitly describes penetration or an active sex act (fucking, entering, moving inside, rhythm, cumming, etc.)
3. Return nude if: undressing, removing clothes, baring chest/body, naked body described, striptease, foreplay with nudity, caressing naked body
4. If active sex is happening but the position is unclear — return missionary
5. Analyze ONLY the last messages"""


async def detect_sex_scene(
    recent_messages: list[dict],
    llm_client,
    language: str = "ru",
) -> Optional[str]:
    """
    Определяет тип контента из последних сообщений диалога.

    Args:
        recent_messages: Последние 2-4 сообщения [{role, content}, ...]
        llm_client: LLM клиент для запроса
        language: Язык диалога ("ru" или "en")

    Returns:
        - Название позы (str) если активный секс → пул фоток
        - "nude" если раздевание/нюдс → ComfyUI Moody
        - None если обычный контент → ComfyUI ZIT
    """
    if not recent_messages:
        return None

    # Быстрый детект: если последнее сообщение юзера содержит "покажи X" → сразу nude
    last_user_msg = next(
        (m.get("content", "") for m in reversed(recent_messages) if m.get("role") == "user"),
        ""
    )
    if last_user_msg:
        pattern = _SHOW_NUDE_PATTERN_EN if language == "en" else _SHOW_NUDE_PATTERN_RU
        if pattern.search(last_user_msg):
            logger.info("Fast nude detection triggered by show-body request")
            return "nude"

    # Выбираем системный промпт и метки ролей по языку
    is_en = language == "en"
    system_prompt = DETECTION_SYSTEM_PROMPT_EN if is_en else DETECTION_SYSTEM_PROMPT
    role_assistant = "Girl" if is_en else "Девушка"
    role_user = "Man" if is_en else "Мужчина"
    dialog_label = "Dialogue:" if is_en else "Диалог:"
    scene_label = "Scene type?" if is_en else "Тип сцены?"

    # Формируем контекст из последних сообщений
    context_parts = []
    for msg in recent_messages[-4:]:
        role = role_assistant if msg.get("role") == "assistant" else role_user
        content = msg.get("content", "")[:300]
        context_parts.append(f"{role}: {content}")

    context = "\n".join(context_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{dialog_label}\n{context}\n\n{scene_label}"},
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
