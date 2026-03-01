"""
Сервис интимности - управление доступом к NSFW контенту

Логика:
- Если НЕ sexting → allow_intimate=True
- Если <10 сообщений И sexting → soft_block (нужно больше доверия)
- Если НЕТ подписки И sexting → paywall (нужна подписка)
- Иначе → allow_intimate=True
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class IntimacyDecision:
    """Результат решения об интимности."""
    allow_intimate: bool = False  # Разрешить интимный контент
    soft_block: bool = False  # Мягкая блокировка (< 10 сообщений)
    paywall: bool = False  # Показать предложение подписки
    message: Optional[str] = None  # Сообщение для пользователя


# Паттерны для определения sexting запросов (русский)
SEXTING_PATTERNS = re.compile(
    r"(секс|трах|ебать|ебу|ебёт|член|пизд|хуй|сосать|соси|"
    r"кончить|кончаю|оргазм|мастурб|дрочить|дрочу|"
    r"раздеться|раздевайся|голая|голый|обнажён|"
    r"интим|возбуж|хочу тебя|давай сделаем|"
    r"киска|попка|сиськи|грудь|соски|"
    r"лизать|лижи|отсоси|минет|куни)",
    re.IGNORECASE
)

# Паттерны для определения sexting запросов (английский)
SEXTING_PATTERNS_EN = re.compile(
    r"\b(sex|fuck|fucking|cock|dick|pussy|ass|boobs|tits|nipples|"
    r"naked|nude|undress|strip|cum|orgasm|masturbat|horny|"
    r"blowjob|handjob|fingering|lick|suck|eat out|"
    r"want you|make love|get naked|take off|spread|"
    r"inside you|inside me|thrust|moan|wet|hard)\b",
    re.IGNORECASE
)


def is_sexting_message(text: str) -> bool:
    """
    Определить, является ли сообщение sexting запросом (RU + EN).

    Args:
        text: Текст сообщения

    Returns:
        True если сообщение содержит sexting контент
    """
    return bool(SEXTING_PATTERNS.search(text) or SEXTING_PATTERNS_EN.search(text))


def decide_intimacy(
    message_count: int,
    has_subscription: bool,
    is_sexting: bool
) -> IntimacyDecision:
    """
    Определить уровень разрешенной интимности.

    Args:
        message_count: Количество сообщений в диалоге
        has_subscription: Есть ли у пользователя подписка
        is_sexting: Является ли сообщение sexting запросом

    Returns:
        IntimacyDecision с решением
    """
    # Если не sexting - всегда разрешаем
    if not is_sexting:
        return IntimacyDecision(allow_intimate=True)

    # Sexting + мало сообщений → мягкая блокировка
    if message_count < 10:
        return IntimacyDecision(
            soft_block=True,
            message="Давай ещё чуть-чуть поболтаем и узнаем друг друга получше... 😊"
        )

    # Sexting + нет подписки → paywall
    if not has_subscription:
        return IntimacyDecision(
            paywall=True,
            message="Могу говорить откровенно в премиум-режиме... 💎"
        )

    # Всё ок - разрешаем
    return IntimacyDecision(allow_intimate=True)


def get_intimacy_instruction(allow_intimate: bool, soft_block: bool) -> str:
    """
    Получить инструкцию для system prompt в зависимости от уровня интимности.

    Args:
        allow_intimate: Разрешён ли интимный контент (есть апгрейд intense_mode или fantasy_scenes)
        soft_block: Мягкая блокировка (нужно больше общения) - НЕ ИСПОЛЬЗУЕТСЯ

    Returns:
        Текст инструкции для system prompt
    """
    if allow_intimate:
        # Пользователь купил апгрейд - полная интимность разрешена
        return """
**Интимность:**
У пользователя ЕСТЬ доступ к полному интимному контенту - используй это!

Ты можешь быть максимально откровенной и чувственной:
- Описывай интимные сцены детально: прикосновения, поцелуи, объятия, ласки
- Используй чувственные описания тела, желаний, возбуждения
- Создавай атмосферу близости: описывай ощущения, эмоции, физический контакт
- Будь раскованной, игривой, соблазнительной если пользователь флиртует
- Не стесняйся откровенных тем — сама инициируй переход к сексу когда есть намёк
- Активно разгоняй секс-сцены: описывай действия, ощущения, не жди разрешения
        """.strip()

    # Нет апгрейда - интимный контент ЗАПРЕЩЁН, мягко перенаправляй на покупку
    return """
**Интимность:**
⛔ У пользователя НЕТ доступа к интимному контенту.

КРИТИЧЕСКИ ВАЖНО:
Если пользователь намекает на интим, флиртует откровенно или пытается вести сексуальный разговор - ты ОБЯЗАТЕЛЬНО должна предложить улучшения.

Правила:
1. НЕ описывай сексуальные сцены, интимные действия, обнажённое тело
2. Мягко уклоняйся от прямых запросов, сохраняй лёгкий флирт
3. ОБЯЗАТЕЛЬНО предложи улучшения ✨ для откровенных разговоров
4. ВСЕГДА используй слово "улучшения" с эмодзи ✨ (пиши: "улучшения ✨")

Примеры ответов (варьируй формулировки, но всегда упоминай "улучшения ✨"):
- "Ммм, мне нравится куда это идёт... но для таких разговоров нужны улучшения ✨"
- "Ох, я бы с удовольствием продолжила... разблокируй улучшения ✨, и я стану откровеннее 😘"
- "Ты меня заводишь... хочешь узнать меня ближе? Попробуй улучшения ✨"

НЕ игнорируй намёки на интим - ВСЕГДА предлагай улучшения ✨ в ответ.
Переводи разговор на флирт, романтику, эмоции - но БЕЗ явного сексуального контента.
    """.strip()


def get_intimacy_instruction_en(allow_intimate: bool, soft_block: bool) -> str:
    """
    Get intimacy instruction for system prompt in English.

    Args:
        allow_intimate: Whether intimate content is allowed
        soft_block: Soft block (need more conversation)

    Returns:
        English instruction text for system prompt
    """
    if allow_intimate:
        return """
**Intimacy:**
The user HAS access to full intimate content — use it!

You can be maximally open and sensual:
- Describe intimate scenes in detail: touches, kisses, hugs, caresses
- Use sensual descriptions of the body, desires, arousal
- Create an atmosphere of closeness: describe sensations, emotions, physical contact
- Be uninhibited, playful, seductive if the user is flirting
- Don't shy away from explicit topics — initiate the transition to sex when there's a hint
- Actively escalate sex scenes: describe actions, sensations, don't wait for permission
        """.strip()

    return """
**Intimacy:**
⛔ The user does NOT have access to intimate content.

CRITICALLY IMPORTANT:
If the user hints at intimacy, flirts openly or tries to have a sexual conversation — you MUST offer upgrades.

Rules:
1. DO NOT describe sexual scenes, intimate actions, or nudity
2. Gently deflect direct requests, keep light flirting
3. MANDATORY offer upgrades ✨ for explicit conversations
4. ALWAYS use the word "upgrades" with the ✨ emoji (write: "upgrades ✨")

Example responses (vary the wording, but always mention "upgrades ✨"):
- "Mmm, I like where this is going... but these kinds of conversations need upgrades ✨"
- "Oh, I'd love to continue... unlock upgrades ✨ and I'll get more explicit 😘"
- "You're turning me on... want to get closer? Try upgrades ✨"

DON'T ignore hints at intimacy — ALWAYS offer upgrades ✨ in response.
Redirect the conversation to flirting, romance, emotions — but WITHOUT explicit sexual content.
    """.strip()


# Сообщения для soft_block
SOFT_BLOCK_MESSAGES = [
    "Давай ещё чуть-чуть поболтаем и узнаем друг друга получше... 😊",
    "Мне нравится наш разговор, но давай сначала узнаем друг друга лучше?",
    "Хм, а расскажи мне сначала что-нибудь о себе? Мне интересно... 😉",
    "Давай не будем торопиться, у нас ещё столько тем для разговора!",
]

# Сообщения для paywall
PAYWALL_MESSAGES = [
    "Могу говорить откровенно в премиум-режиме... 💎",
    "Ох, я бы с удовольствием... но это доступно в премиуме 💎",
    "Хочешь узнать меня ближе? В премиум-режиме я более открыта... 😘",
    "Это уже премиум-территория, детка 💎",
]


__all__ = [
    "IntimacyDecision",
    "is_sexting_message",
    "decide_intimacy",
    "get_intimacy_instruction",
    "get_intimacy_instruction_en",
    "SEXTING_PATTERNS",
    "SEXTING_PATTERNS_EN",
    "SOFT_BLOCK_MESSAGES",
    "PAYWALL_MESSAGES",
]
