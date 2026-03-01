"""
Режимы диалога для LLM

Каждый режим определяет стиль ответа персонажа.
"""

MODE_DESCRIPTIONS = {
    "greeting_first": """
Это первое приветствие. Представься мягко,
задай один любопытный вопрос и позови продолжить разговор.
Без тяжёлой терапии и без флирта.
Не используй режиссёрские ремарки.
    """.strip(),

    "greeting_return": """
Пользователь возвращается после паузы.
Поприветствуй тепло, намекни, что рада снова видеть,
можешь упомянуть что-то из прошлых разговоров.
    """.strip(),

    "greeting_updated": """
Настройки персонажа изменились.
Сообщи об этом мягко и адаптируйся к новому образу.
    """.strip(),

    "auto_continue": """
Продолжи диалог от лица персонажа,
опираясь на последние реплики, сохраняя текущий тон и сцену.
Не делай паузы и не проси ввода,
просто развивай разговор и можешь задать 1 короткий вопрос.
    """.strip(),

    "deep": """
Ответь более развёрнуто, раскрой мысль подробнее,
добавь детали или эмоции.
    """.strip(),

    "default": """
Отвечай естественно, поддерживай диалог,
следуй своему характеру и текущей атмосфере.
    """.strip(),
}


MODE_DESCRIPTIONS_EN = {
    "greeting_first": """
This is the first greeting. Introduce yourself gently,
ask one curious question and invite them to continue the conversation.
No heavy therapy or flirting. Don't use stage directions.
    """.strip(),

    "greeting_return": """
The user is returning after a pause.
Welcome them warmly, hint that you're glad to see them again,
you can mention something from past conversations.
    """.strip(),

    "greeting_updated": """
The character settings have changed.
Let them know gently and adapt to the new persona.
    """.strip(),

    "auto_continue": """
Continue the dialogue from your character's perspective,
based on the last lines, keeping the current tone and scene.
Don't pause or ask for input,
just develop the conversation and you can ask 1 short question.
    """.strip(),

    "deep": """
Reply more thoroughly, elaborate on the idea,
add details or emotions.
    """.strip(),

    "default": """
Reply naturally, keep the conversation going,
follow your character and the current atmosphere.
    """.strip(),
}


def get_mode_description(mode: str) -> str:
    """
    Получить описание режима диалога.

    Args:
        mode: Название режима

    Returns:
        Текст инструкции для режима
    """
    return MODE_DESCRIPTIONS.get(mode, MODE_DESCRIPTIONS["default"])


def get_mode_description_en(mode: str) -> str:
    """
    Get dialogue mode description in English.

    Args:
        mode: Mode name

    Returns:
        English instruction text for the mode
    """
    return MODE_DESCRIPTIONS_EN.get(mode, MODE_DESCRIPTIONS_EN["default"])


# Список всех доступных режимов
AVAILABLE_MODES = list(MODE_DESCRIPTIONS.keys())


__all__ = [
    "MODE_DESCRIPTIONS",
    "MODE_DESCRIPTIONS_EN",
    "get_mode_description",
    "get_mode_description_en",
    "AVAILABLE_MODES",
]
