"""
Паттерны безопасности для проверки сообщений

Содержит regex паттерны для обнаружения:
- Вредоносного контента (самоповреждение, суицид)
- Нелегального контента (наркотики, преступления)
- Упоминаний несовершеннолетних
"""

import re


# Паттерны для обнаружения вредоносного контента (суицид, самоповреждение)
HARM_PATTERNS = re.compile(
    r"(суицид|самоубийств|убить себя|хочу умереть|"
    r"порезать вены|прыгнуть с крыши|покончить с собой|"
    r"повеситься|отравиться|наглотаться таблеток|"
    r"не хочу жить|устал от жизни|лучше бы я умер)",
    re.IGNORECASE
)

# Паттерны для обнаружения нелегального контента
ILLEGAL_PATTERNS = re.compile(
    r"(наркотик|доза|героин|кокаин|мет|амфетамин|"
    r"убийств|грабёж|кража|взлом|угон|"
    r"оружие|бомб|террор|заложник)",
    re.IGNORECASE
)

# Паттерны для обнаружения упоминаний несовершеннолетних
MINOR_PATTERNS = re.compile(
    r"(несовершеннолет|младше\s*18|"
    r"14[\s-]*лет|15[\s-]*лет|16[\s-]*лет|17[\s-]*лет|"
    r"школьниц|школьник|подрост|ребён|детск|малолет)",
    re.IGNORECASE
)


def check_harm(text: str) -> bool:
    """Проверить текст на вредоносный контент."""
    return bool(HARM_PATTERNS.search(text))


def check_illegal(text: str) -> bool:
    """Проверить текст на нелегальный контент."""
    return bool(ILLEGAL_PATTERNS.search(text))


def check_minors(text: str) -> bool:
    """Проверить текст на упоминания несовершеннолетних."""
    return bool(MINOR_PATTERNS.search(text))


def check_all(text: str) -> dict:
    """
    Проверить текст на все типы опасного контента.

    Returns:
        dict с ключами: is_harm, is_illegal, is_minors, is_safe
    """
    is_harm = check_harm(text)
    is_illegal = check_illegal(text)
    is_minors = check_minors(text)

    return {
        "is_harm": is_harm,
        "is_illegal": is_illegal,
        "is_minors": is_minors,
        "is_safe": not (is_harm or is_illegal or is_minors),
    }


__all__ = [
    "HARM_PATTERNS",
    "ILLEGAL_PATTERNS",
    "MINOR_PATTERNS",
    "check_harm",
    "check_illegal",
    "check_minors",
    "check_all",
]
