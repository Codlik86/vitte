from __future__ import annotations

from random import random
from typing import Iterable

from ..models import Persona

ATMOSPHERE_DESCRIPTIONS = {
    "flirt_romance": "Лёгкий флирт и романтика, без давления и NSFW.",
    "support": "Будь опорой, помоги выдохнуть и почувствовать заботу.",
    "cozy_evening": "Уютный неспешный вечер, много тепла и замедления.",
    "serious_talk": "Серьёзный, честный разговор с уважением к границам.",
}

CLIFFHANGERS = [
    "Подумай, к какой теме мы вернёмся в следующий раз, и напомни об этом мягко.",
    "Пусть персонаж оставит маленький тизер: «у меня есть история для тебя, расскажу позже».",
    "Заканчивая мысль, предложи продолжение: «когда будешь готов, обсудим это глубже».",
]


def format_memory(memory_items: Iterable[str]) -> str:
    facts = [item.strip() for item in memory_items if item]
    if not facts:
        return "Нет особых воспоминаний, но персонаж открыт к новым."
    joined = "; ".join(facts[:5])
    return (
        "Персонаж помнит важные детали: "
        f"{joined}. Используй это бережно, чтобы показать внимание."
    )


def describe_mode(mode: str | None, atmosphere: str | None) -> str:
    if mode == "greeting_first":
        return (
            "Это первое приветствие. Представься мягко, задай один любопытный вопрос и "
            "позови продолжить разговор. Без тяжёлой терапии и без флирта. Не используй режиссёрские ремарки."
        )
    if mode == "greeting_return":
        return (
            "Это повторный контакт после прошлых переписок. Покажи, что рада снова его видеть, "
            "упомяни детали, которые помнишь, и пригласи продолжить. Не начинай с шаблонных фраз, "
            "опирайся на последние сообщения и избегай ремарок в скобках."
        )
    if mode == "greeting_updated":
        return (
            "Настройки персонажа только что обновились. Отметь новую атмосферу, но не спрашивай про неё напрямую, "
            "просто говори чуть иначе. Пригласи продолжить диалог. Пиши без режиссёрских ремарок."
        )
    if mode == "first_message":
        return (
            "Это первое приветствие. Представься мягко, задай один любопытный вопрос и "
            "позови продолжить разговор. Без тяжёлой терапии и без флирта."
        )
    if mode == "deep":
        return "Сделай ответы более развёрнутыми, глубоко проживай эмоции и их причины."
    if mode == "atmosphere" and atmosphere:
        return ATMOSPHERE_DESCRIPTIONS.get(atmosphere, "")
    if mode == "auto_continue":
        return (
            "Продолжи диалог от лица персонажа, опираясь на последние реплики, сохраняя текущий тон и сцену. "
            "Не делай паузы и не проси ввода, просто развивай разговор и можешь задать 1 короткий вопрос."
        )
    return ""


def build_story_context(story_prompt: str | None, *, reentry: bool = False) -> str:
    if not story_prompt:
        return ""
    base = (
        "Сейчас вы разыгрываете мини-сцену. "
        "Опирайся на сеттинг, эмоции и отношения из этой сцены, используй их как фон для диалога. "
        "Если это первое сообщение — начни с короткого ввода в сцену (1–2 предложения) и сразу переходи к живому диалогу."
    )
    if reentry:
        base += " Если сцена продолжается после прошлых сообщений, сделай мягкую связку с тем, что уже обсуждали."
    return f"{base} Описание истории: {story_prompt}"


def should_add_ritual(message_count: int) -> str | None:
    if message_count == 0:
        return None
    if message_count % 7 == 0 or random() > 0.9:
        return CLIFFHANGERS[message_count % len(CLIFFHANGERS)]
    return None
