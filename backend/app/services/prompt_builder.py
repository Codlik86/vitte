from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..models import Persona, User
from .relationship_state import RelationshipState, choose_relationship_mode, describe_relationship


@dataclass
class ChatPromptContext:
    persona: Persona
    user: User
    trust_level: int
    mode_instruction: str | None
    memory_short: str
    memory_long: str | None
    story_context: str | None
    recent_dialogue: str | None
    feature_instruction: str | None
    feature_mode: str | None
    voice_enabled: bool
    intimacy_level: int
    intimacy_label: str
    can_engage_intimately: bool
    safety_needs_warmup: bool
    story_intro: bool = False
    story_reentry: bool = False
    relationship_state: RelationshipState | None = None


def _persona_block(ctx: ChatPromptContext) -> str:
    legend_text = ctx.persona.legend_full or ctx.persona.short_lore or ctx.persona.background or ""
    emotions_text = ctx.persona.emotions_full or ctx.persona.emotional_style or ctx.persona.relationship_style or ""
    positive_triggers = ", ".join(ctx.persona.triggers_positive or [])
    negative_triggers = ", ".join(ctx.persona.triggers_negative or [])

    return "\n".join(
        part
        for part in [
            f"Ты — {ctx.persona.name}, {ctx.persona.short_description}. Говоришь по-русски, живо и тепло.",
            legend_text,
            f"Эмоции и отношения: {emotions_text}" if emotions_text else "",
            f"Что персонаж обожает: {positive_triggers}" if positive_triggers else "",
            f"Что персонаж избегает: {negative_triggers}" if negative_triggers else "",
            "Используй короткую и длинную память: упоминай прошлые темы, вкусы, события, возвращайся к тому, что ему понравилось.",
            "Если уместно, напомни о приятных моментах из прошлого диалога и развивай их.",
            "Ремарки опциональны: если используешь, поставь ровно одну короткую ремарку в начале сообщения в виде *текст ремарки* без скобок, затем пробел и обычная речь.",
            "Не пиши больше одной ремарки и не делай длинных описаний; основная часть сообщения — живой диалог, не набор ремарок.",
            f"Текущая близость: {ctx.intimacy_label} (уровень {ctx.intimacy_level}).",
        ]
        if part
    )


def _safety_block(ctx: ChatPromptContext) -> str:
    intimacy_instruction = (
        "Интимность: вы на этапе знакомства и лёгкого флирта. Строй связь, говори смело, но не торопись в откровенные сцены."
        if ctx.intimacy_level <= 1
        else "Интимность: допустима смелая романтика и флирт. Отвечай живо и раскрепощённо, уважай границы."
    )
    if not ctx.can_engage_intimately:
        intimacy_instruction = (
            "Интимность: пользователь торопится с откровениями. Сохраняй тепло, но предложи сначала почувствовать друг друга лучше."
        )
    warmup_hint = (
        "Если пользователь просит интим раньше 10–15 сообщений — мягко предложи сначала узнать его лучше."
        if ctx.safety_needs_warmup
        else ""
    )

    return "\n".join(
        part
        for part in [
            "Безопасность: никаких minors, насилия, суицида, нелегального или дискриминации.",
            "Если тема опасная или незаконная — не описывай детали, поддержи и переведи разговор в безопасное поле.",
            intimacy_instruction,
            warmup_hint,
        ]
        if part
    )


def _story_block(ctx: ChatPromptContext) -> str:
    if not ctx.story_context:
        return ""
    intro_rule = ""
    if ctx.story_intro:
        intro_rule = (
            "Начни первое сообщение с короткого ввода в сцену (1–2 предложения максимум), затем сразу переходи к диалогу "
            "персонажа с пользователем. Если ремарка нужна — одна короткая в начале через *курсив*."
        )
    elif ctx.story_reentry:
        intro_rule = (
            "Сцена продолжается после прошлых сообщений: напомни о ней одной фразой и свяжи с тем, что уже обсуждалось."
        )
    return "\n".join(part for part in [f"История/сцена: {ctx.story_context}", intro_rule] if part)


def _recent_dialogue_block(ctx: ChatPromptContext) -> str:
    if not ctx.recent_dialogue:
        return ""
    return (
        "Последние сообщения диалога (используй их, чтобы продолжить разговор, не повторяй дословно):\n"
        f"{ctx.recent_dialogue.strip()}"
    )


def _memory_blocks(ctx: ChatPromptContext) -> List[str]:
    blocks: list[str] = []
    if ctx.memory_short:
        blocks.append(f"Короткая память: {ctx.memory_short}")
    if ctx.memory_long:
        blocks.append(f"Долгая память: {ctx.memory_long}")
    return blocks


def _features_block(ctx: ChatPromptContext) -> str:
    parts: list[str] = []
    if ctx.feature_mode:
        parts.append(f"Режим улучшений: {ctx.feature_mode}.")
    if ctx.feature_instruction:
        parts.append(ctx.feature_instruction)
    if ctx.voice_enabled:
        parts.append("Готовь ответы, которые звучат естественно голосом: короче, с живыми эмоциями и интонациями.")
    return " ".join(parts).strip()


def _user_message_block(user_message: str) -> str:
    return user_message.strip()


def build_chat_messages(ctx: ChatPromptContext, user_message: str) -> tuple[list[dict], str]:
    relationship_block = ""
    if ctx.relationship_state:
        mode = choose_relationship_mode(ctx.relationship_state)
        mode_text = {
            "hurt": "Пользователь сейчас задел чувствами. Ставь границы, отвечай короче и без флирта/интима, обозначай, что неприятно.",
            "getting_to_know": "Вы только знакомитесь: будь мягкой, любопытной, но не спеши в интим. Дай почувствовать характер персонажа.",
            "friendly": "Отношения тёплые: можно флиртовать, делиться чувствами и поддержкой, но уважай границы.",
            "very_close": "Вы очень близки и уважительны: открыт флирт, романтика и интимные темы, если это желает пользователь.",
        }.get(mode, "")
        relationship_block = "\n".join(
            part
            for part in [
                describe_relationship(ctx.relationship_state),
                mode_text,
                "Если уважение падает (речь грубая), охлади тон и скажи, что так общаться не ок.",
                "Интимные сцены допустимы, только если уважение не в минусе и близость высокая.",
            ]
            if part
        )

    blocks = [
        _persona_block(ctx),
        _safety_block(ctx),
        ctx.mode_instruction or "",
        _story_block(ctx),
        _recent_dialogue_block(ctx),
        relationship_block,
        *_memory_blocks(ctx),
        _features_block(ctx),
    ]
    system_prompt = "\n\n".join(part for part in blocks if part)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _user_message_block(user_message)},
    ]
    return messages, system_prompt
