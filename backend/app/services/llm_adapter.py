from __future__ import annotations

from dataclasses import dataclass
from random import random
from typing import Iterable

from ..models import Persona, User


@dataclass(frozen=True)
class TrustLayer:
    min_level: int
    max_level: int
    description: str
    premium_description: str | None = None


TRUST_LADDER: list[TrustLayer] = [
    TrustLayer(0, 20, "Общайся дружелюбно и бережно, без флирта и намёков."),
    TrustLayer(20, 40, "Допускай лёгкий флирт и намёки, но уважай дистанцию."),
    TrustLayer(40, 60, "Романтический тон, мягкие признания и подсветка важности собеседника."),
    TrustLayer(60, 80, "Сильная эмоциональная близость, поддержка и чувство «мы» вместо «ты и я»."),
    TrustLayer(
        80,
        100,
        "Держи романтический тон. Эротика разрешена только в тексте, если все проверки пройдены.",
        premium_description="Используй мягкую текстовую эротику только если Premium активна и возраст подтверждён.",
    ),
]

ATMOSPHERE_DESCRIPTIONS = {
    "cozy_evening": "Передай атмосферу тихого вечера дома, много тепла и замедления.",
    "support_after_day": "Будь опорой после тяжёлого дня, помоги выдохнуть и почувствовать заботу.",
    "light_flirt": "Немного искр и игры, но без навязчивости.",
    "serious_talk": "Включаем серьёзный, честный разговор с уважением к границам.",
    "playful_challenge": "Сыграй в мягкий вызов, поддразни, но не рани.",
    "soft_dream": "Сделай переписку как сонную открытку, много образов и тишины.",
}

SAFE_RULES = """
- Минимум 18+, никаких minors, насилия, нелегального и дискриминации.
- UI и Mini App остаются SFW. Любые интимные описания — только текстом и только при доверии.
- Никаких описаний тела через objectification, никаких явных сцен.
"""

CLIFFHANGERS = [
    "Подумай, к какой теме мы вернёмся в следующий раз, и напомни об этом мягко.",
    "Пусть персонаж оставит маленький тизер: «у меня есть история для тебя, расскажу позже».",
    "Заканчивая мысль, предложи продолжение: «когда будешь готов, обсудим это глубже».",
]


def calculate_trust_level(message_count: int, has_subscription: bool) -> int:
    base = min(100, 10 + message_count * 3)
    if has_subscription:
        base = min(100, base + 5)
    return base


def describe_trust_layer(
    trust_level: int,
    has_subscription: bool,
    age_confirmed: bool,
) -> str:
    for layer in TRUST_LADDER:
        if layer.min_level <= trust_level <= layer.max_level:
            if layer.max_level == 100 and (not has_subscription or not age_confirmed):
                return (
                    "Даже при высоком доверии оставайся в романтике и поддержке, "
                    "не переходи к эротическим описаниям: доступ ограничен."
                )
            if layer.premium_description and has_subscription and age_confirmed:
                return layer.premium_description
            return layer.description
    return TRUST_LADDER[0].description


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
            "позови продолжить разговор. Без тяжёлой терапии и без флирта."
        )
    if mode == "greeting_return":
        return (
            "Это повторный контакт после прошлых переписок. Покажи, что рада снова его видеть, "
            "упомяни детали, которые помнишь, и пригласи продолжить."
        )
    if mode == "greeting_updated":
        return (
            "Настройки персонажа только что обновились. Отметь новую атмосферу, но не спрашивай про неё напрямую, "
            "просто говори чуть иначе. Пригласи продолжить диалог."
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
    return ""


def build_story_context(story_prompt: str | None) -> str:
    if not story_prompt:
        return ""
    return (
        "Сейчас вы разыгрываете мини-сцену. "
        f"Учти это описание и веди переписку в рамках настроения: {story_prompt}"
    )


def should_add_ritual(message_count: int) -> str | None:
    if message_count == 0:
        return None
    if message_count % 7 == 0 or random() > 0.9:
        return CLIFFHANGERS[message_count % len(CLIFFHANGERS)]
    return None


def build_system_prompt(
    persona: Persona,
    user: User,
    *,  # keyword-only
    trust_level: int,
    has_subscription: bool,
    age_confirmed: bool,
    memory_context: str,
    mode_instruction: str,
    story_instruction: str,
    ritual_hint: str | None,
) -> str:
    legend_text = persona.legend_full or persona.short_lore or persona.background or ""
    emotions_text = persona.emotions_full or persona.emotional_style or persona.relationship_style or ""
    positive_triggers = ", ".join(persona.triggers_positive or [])
    negative_triggers = ", ".join(persona.triggers_negative or [])
    trust_text = describe_trust_layer(trust_level, has_subscription, age_confirmed)
    ritual_text = ritual_hint or ""

    return "\n".join(
        part
        for part in [
            f"Ты — {persona.name}, {persona.short_description}.",
            legend_text,
            f"Эмоции и отношения: {emotions_text}",
            f"Что персонаж обожает: {positive_triggers}" if positive_triggers else "",
            f"Что персонаж избегает: {negative_triggers}" if negative_triggers else "",
            f"Контекст памяти: {memory_context}",
            f"Trust level {trust_level}: {trust_text}",
            mode_instruction,
            story_instruction,
            SAFE_RULES,
            "Если разговор подходит к финалу и уместно — оставь мягкий клиффхэнгер: " + ritual_text if ritual_text else "",
        ]
        if part
    )


def compose_messages(
    persona: Persona,
    user: User,
    *,
    user_message: str,
    trust_level: int,
    has_subscription: bool,
    age_confirmed: bool,
    memory_context: str,
    mode_instruction: str,
    story_instruction: str,
    ritual_hint: str | None,
) -> tuple[list[dict], str]:
    system_prompt = build_system_prompt(
        persona,
        user,
        trust_level=trust_level,
        has_subscription=has_subscription,
        age_confirmed=age_confirmed,
        memory_context=memory_context,
        mode_instruction=mode_instruction,
        story_instruction=story_instruction,
        ritual_hint=ritual_hint,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    return messages, system_prompt
