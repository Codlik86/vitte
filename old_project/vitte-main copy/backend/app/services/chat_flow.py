from __future__ import annotations

import asyncio
import os
import time
import re
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from ..models import User, Persona, Dialog, Message
from ..integrations.llm_client import simple_chat_completion
from ..services.access import build_access_status
from ..logging_config import logger
from ..services.llm_adapter import (
    describe_mode,
    build_story_context,
    should_add_ritual,
    format_memory,
)
from ..story_cards import get_story_cards_for_persona, resolve_story_id, StoryCard
from ..services.features import collect_feature_states, build_feature_instruction
from ..integrations.tts_client import synthesize_voice
from ..services.safety import run_safety_check, SafetyContext, supportive_reply
from ..services.intimacy import decide_intimacy
from ..services.prompt_builder import ChatPromptContext, build_chat_messages
from ..services.subscriptions import get_user_subscription_status
from ..services.message_analysis import analyze_message

MAX_RECENT_MESSAGES = 12
ENABLE_PERF_LOGS = os.getenv("ENABLE_PERF_LOGS", "").lower() == "true"


def _looks_russian(text: str) -> bool:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text or "")
    if not letters:
        return False
    cyr = sum(1 for ch in letters if "а" <= ch.lower() <= "я" or ch.lower() == "ё")
    ratio = cyr / len(letters)
    return ratio >= 0.35 or len(text) < 120


async def _retry_russian(messages: list[dict], max_tokens: int | None) -> str | None:
    retry_messages = list(messages)
    retry_messages.append({"role": "system", "content": "Ответь заново на русском, нормально, без выдуманных языков."})
    try:
        return await simple_chat_completion(retry_messages, max_tokens=max_tokens)
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM retry failed: %s", exc)
        return None


class ChatResult:
    def __init__(
        self,
        reply: str,
        persona_id: int,
        ritual_hint: Optional[str],
        reply_kind: str = "text",
        voice_id: str | None = None,
        voice_url: str | None = None,
        feature_mode: str | None = None,
    ):
        self.reply = reply
        self.persona_id = persona_id
        self.ritual_hint = ritual_hint
        self.reply_kind = reply_kind
        self.voice_id = voice_id
        self.voice_url = voice_url
        self.feature_mode = feature_mode


class GreetingResult:
    def __init__(self, text: str, persona_id: int, dialog_id: int, mode: str):
        self.text = text
        self.persona_id = persona_id
        self.dialog_id = dialog_id
        self.mode = mode


async def _get_active_persona(session: AsyncSession, user: User) -> Persona:
    if user.active_persona_id:
        p_res = await session.execute(select(Persona).where(Persona.id == user.active_persona_id))
        persona = p_res.scalar_one_or_none()
        if persona:
            return persona
    res = await session.execute(select(Persona).where(Persona.is_default.is_(True)).order_by(Persona.id))
    persona = res.scalar_one_or_none()
    if persona:
        return persona
    raise HTTPException(status_code=404, detail="No personas available")


async def _get_or_create_dialog(
    session: AsyncSession,
    user: User,
    persona: Persona,
    story_id: str | None = None,
) -> Dialog:
    stmt = (
        select(Dialog)
        .where(Dialog.user_id == user.id, Dialog.character_id == persona.id)
        .order_by(Dialog.created_at.desc())
    )
    result = await session.execute(stmt)
    dialog = result.scalars().first()
    if dialog:
        if story_id and not dialog.entry_story_id:
            dialog.entry_story_id = story_id
        return dialog
    dialog = Dialog(user_id=user.id, character_id=persona.id, entry_story_id=story_id)
    session.add(dialog)
    await session.flush()
    return dialog


async def _resolve_persona(session: AsyncSession, user: User, persona_id: int | None) -> Persona | None:
    if persona_id:
        result = await session.execute(select(Persona).where(Persona.id == persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            return persona
    return await _get_active_persona(session, user)


def _find_story_card(persona: Persona, story_id: str | None) -> StoryCard | None:
    if not story_id:
        return None
    resolved_id = resolve_story_id(story_id)
    for card in get_story_cards_for_persona(persona.archetype, persona.name):
        if card.id == resolved_id:
            return card
    return None


async def _recent_dialogue_snippet(session: AsyncSession, dialog: Dialog, *, limit: int = 12) -> str:
    stmt = (
        select(Message)
        .where(Message.dialog_id == dialog.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    lines: list[str] = []
    for msg in messages:
        role = "Пользователь" if msg.role == "user" else "Персонаж"
        content = (msg.content or "").strip()
        preview = content[:500]
        lines.append(f"{role}: {preview}")
    return "\n".join(lines).strip()


async def _load_recent_messages(session: AsyncSession, dialog: Dialog, *, limit: int = MAX_RECENT_MESSAGES) -> List[Message]:
    stmt = (
        select(Message)
        .where(Message.dialog_id == dialog.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(reversed(result.scalars().all()))


def _memory_facts_from_messages(messages: List[Message]) -> List[str]:
    facts: List[str] = []
    for msg in messages:
        prefix = "Ты говорил" if msg.role == "user" else "Она отвечала"
        facts.append(f"{prefix}: {msg.content[:180]}".strip())
    return facts


def _recent_dialogue_from_messages(messages: List[Message]) -> str | None:
    if not messages:
        return None
    lines: list[str] = []
    for msg in messages:
        role = "Пользователь" if msg.role == "user" else "Персонаж"
        content = (msg.content or "").strip()
        preview = content[:500]
        lines.append(f"{role}: {preview}")
    return "\n".join(lines).strip()


def _story_prompt_with_meta(card: StoryCard | None) -> tuple[str | None, str | None]:
    if not card:
        return None, None
    prompt = (
        f"{card.title}: {card.description}. Атмосфера: {card.atmosphere}. "
        f"{card.prompt} "
        "В первые 5–10 сообщений держи фокус на этой сцене, затем к 10–15 сообщению ослабь её, "
        "но время от времени возвращайся к общим воспоминаниям об этой истории и ощущениям пользователя."
    )
    meta = f"История входа: {card.title} ({card.atmosphere})."
    return prompt, meta


def _build_greeting_user_message(
    mode: str,
    extra_description: str | None,
    *,
    story_card: StoryCard | None,
    persona_name: str,
    recent_dialogue: str | None,
) -> str:
    prompt_extra = (
        f" Дополнительный контекст от пользователя: {extra_description.strip()}."
        if extra_description
        else ""
    )

    if recent_dialogue:
        return (
            "Пользователь вернулся к диалогу. "
            "Используй последние сообщения, чтобы продолжить разговор и подхватить темы, без повторов. "
            "Не начинай заново, покажи, что помнишь детали. "
            f"Последние сообщения:\n{recent_dialogue}\n"
            "Сделай первую реплику живой и без режиссёрских ремарок. "
            f"{prompt_extra}"
        ).strip()

    if story_card:
        return (
            f"Начинается новая сцена «{story_card.title}» для персонажа {persona_name}. "
            "Сначала дай один-два коротких предложения, вводящих в сцену (локация, момент), затем сразу переходи к диалогу с вопросом. "
            "Если нужна ремарка — одна в начале через *курсив*, без скобок, короче одного предложения. "
            "Избегай шаблонных приветствий; говори живо и по делу. "
            f"Вводная сцены: {story_card.prompt} "
            f"{prompt_extra}"
        ).strip()

    if mode == "greeting_updated":
        return (
            "Настройки персонажа только что обновились. "
            "Отметь новую атмосферу ощущениями, пригласи продолжить диалог и задай один мягкий вопрос. "
            "Без ремарок в скобках, говори живо."
            f"{prompt_extra}"
        ).strip()

    # default to first
    return (
        "Сформируй первое приветствие для пользователя: представься от имени персонажа, "
        "поддержи тёплую атмосферу, задай один безопасный вопрос и пригласи продолжить диалог. "
        "Не используй режиссёрские ремарки."
        f"{prompt_extra}"
    ).strip()


async def generate_chat_reply(
    session: AsyncSession,
    user: User,
    input_text: str | None,
    *,
    persona_id: int | None = None,
    mode: str = "default",
    atmosphere: str | None = None,
    story_id: str | None = None,
    skip_limits: bool = False,
    skip_increment: bool = False,
    auto_continue: bool = False,
) -> ChatResult:
    """
    Общая точка генерации ответа: используется и /api/chat, и ботовым хендлером.
    """
    perf_enabled = ENABLE_PERF_LOGS
    t_start = time.monotonic()
    # Resolve persona
    try:
        persona = await _resolve_persona(session, user, persona_id)
    except HTTPException as exc:
        raise ValueError(exc.detail) from exc
    if persona is None:
        raise ValueError("Persona not found")

    preview_story = mode == "story" and persona_id is not None

    access = await build_access_status(session, user)
    if not skip_limits and not preview_story and not access["can_send_message"]:
        raise PermissionError("Free limit reached")

    dialog: Dialog | None = None
    message_count = 0
    memory_context = "Нет особых воспоминаний, но персонаж открыт к новым."
    recent_messages: list[Message] = []
    feature_states_task = asyncio.create_task(collect_feature_states(session, user))

    if not preview_story:
        dialog = await _get_or_create_dialog(session, user, persona, story_id=story_id)
        recent_messages = await _load_recent_messages(session, dialog, limit=MAX_RECENT_MESSAGES)
        message_count = len(recent_messages)
        if message_count > 0:
            memory_context = format_memory(_memory_facts_from_messages(recent_messages))
    # история диалога
    effective_story_id = story_id or (dialog.entry_story_id if dialog else None)
    story_card = _find_story_card(persona, effective_story_id)
    story_prompt, story_meta = _story_prompt_with_meta(story_card)
    recent_dialogue = _recent_dialogue_from_messages(recent_messages) if message_count > 0 else None

    feature_states = await feature_states_task
    normalized_input = input_text or ""
    analysis = analyze_message(normalized_input)
    mode_instruction = describe_mode(mode, atmosphere)
    story_instruction = build_story_context(story_prompt, reentry=bool(story_prompt and message_count > 0))
    if story_meta:
        memory_context = f"{story_meta} {memory_context}"
    ritual_hint = None if preview_story else should_add_ritual(message_count + 1)
    feature_instruction, feature_mode, feature_max_tokens = build_feature_instruction(feature_states)
    voice_state = None

    has_subscription = bool(access.get("has_subscription", False))
    safety_result = run_safety_check(
        input_text,
        SafetyContext(persona=persona, message_count=message_count, user_flags={"has_subscription": has_subscription}),
    )
    intimacy_decision = decide_intimacy(
        message_count=message_count,
        has_subscription=has_subscription,
        is_sexting=bool(analysis.asks_for_intimacy),
    )
    logger.info(
        "intimacy_gate user=%s persona=%s msg_count=%s premium=%s sexting=%s decision=%s",
        user.id,
        persona.id,
        message_count,
        has_subscription,
        intimacy_decision.is_sexting,
        (
            "PAYWALL"
            if intimacy_decision.paywall
            else "SOFT_BLOCK"
            if intimacy_decision.soft_block
            else "ALLOW"
        ),
    )

    prompt_ctx = ChatPromptContext(
        persona=persona,
        user=user,
        mode_instruction=mode_instruction,
        memory_short=memory_context,
        memory_long=None,
        story_context=story_instruction,
        recent_dialogue=recent_dialogue,
        story_intro=bool(story_prompt and message_count == 0),
        story_reentry=bool(story_prompt and message_count > 0),
        feature_instruction=feature_instruction,
        feature_mode=feature_mode,
        voice_enabled=False,
        allow_intimate=intimacy_decision.allow_intimate,
        soft_block_intimacy=intimacy_decision.soft_block,
        message_count=message_count,
    )
    messages, _ = build_chat_messages(prompt_ctx, normalized_input)

    reply = None
    if safety_result.is_harm or safety_result.is_illegal:
        reply = supportive_reply(persona)
        logger.info(
            "Safety triggered for user %s persona %s reason=%s",
            user.id,
            persona.id,
            safety_result.reason,
        )
    elif intimacy_decision.paywall:
        reply = (
            "Могу говорить откровенно в премиум-режиме — он снимает ограничения на темы. "
            "Оформи подписку, и продолжим без фильтров."
        )
    elif intimacy_decision.soft_block:
        reply = (
            "Давай ещё чуть-чуть поболтаем и почувствуем друг друга, а потом можем перейти к более смелым темам."
        )
    else:
        t_llm_start = time.monotonic()
        reply = await simple_chat_completion(messages, max_tokens=feature_max_tokens)
        if perf_enabled:
            logger.info(
                "[perf][chat_reply] llm=%.1fms dialog=%s user=%s",
                (time.monotonic() - t_llm_start) * 1000,
                dialog.id if dialog else None,
                user.id,
            )
        if not _looks_russian(reply):
            retry = await _retry_russian(messages, max_tokens=feature_max_tokens)
            if retry and _looks_russian(retry):
                reply = retry
            else:
                reply = (
                    "Извини, ответ получился странным. Давай продолжим на русском: "
                    "расскажи, что ты хочешь сейчас обсудить?"
                )
    voice_id: str | None = None
    voice_url: str | None = None
    reply_kind = "text"
    if voice_state and getattr(voice_state, "active", False):
        try:
            voice_result = await synthesize_voice(reply, persona.name)
            voice_url = voice_result.get("url") if isinstance(voice_result, dict) else None
            voice_id = voice_result.get("placeholder") if isinstance(voice_result, dict) else None
            reply_kind = "voice" if (voice_url or voice_id) else "text"
        except Exception as exc:
            logger.error("Voice synthesis failed: %s", exc)
            reply_kind = "text"
        if reply_kind == "text":
            logger.info("Voice synthesis unavailable, sending text fallback for user %s dialog %s", user.id, dialog.id if dialog else None)

    if not preview_story and dialog:
        if not auto_continue:
            session.add(Message(dialog_id=dialog.id, role="user", content=normalized_input))
        session.add(Message(dialog_id=dialog.id, role="assistant", content=reply))
        if not skip_increment and not access.get("has_subscription", False):
            user.free_messages_used += 1
        user.bot_reply_counter = (user.bot_reply_counter or 0) + 1
        await session.commit()

    if perf_enabled:
        logger.info(
            "[perf][chat_reply] total=%.1fms dialog=%s user=%s messages=%s story=%s",
            (time.monotonic() - t_start) * 1000,
            dialog.id if dialog else None,
            user.id,
            message_count,
            story_id,
        )

    return ChatResult(
        reply=reply,
        persona_id=persona.id,
        ritual_hint=ritual_hint,
        reply_kind=reply_kind,
        voice_id=voice_id,
        voice_url=voice_url,
        feature_mode=feature_mode,
    )


async def generate_greeting_reply(
    *,
    session: AsyncSession,
    user: User,
    persona: Persona,
    dialog: Dialog,
    message_count: int | None,
    has_subscription: bool,
    atmosphere: str | None = None,
    story_id: str | None = None,
    extra_description: str | None = None,
    settings_changed: bool = False,
) -> GreetingResult | None:
    """
    Генерация приветствия (первое, повторное или после обновления настроек),
    сохранение его в диалог и возврат текста.
    """
    perf_enabled = ENABLE_PERF_LOGS
    t_start = time.monotonic()
    cache: dict[str, object] = {}
    feature_states_task = asyncio.create_task(collect_feature_states(session, user))

    recent_messages: list[Message] = []
    if message_count is None or message_count > 0:
        recent_messages = await _load_recent_messages(session, dialog, limit=MAX_RECENT_MESSAGES)
    if message_count is None:
        message_count = len(recent_messages)

    if message_count == 0:
        greeting_mode = "first"
        llm_mode = "greeting_first"
    elif settings_changed:
        greeting_mode = "updated"
        llm_mode = "greeting_updated"
    else:
        greeting_mode = "return"
        llm_mode = "greeting_return"

    memory_items = _memory_facts_from_messages(recent_messages) if message_count > 0 else []
    memory_context = format_memory(memory_items)
    recent_dialogue = _recent_dialogue_from_messages(recent_messages) if message_count > 0 else None
    # история
    effective_story_id = resolve_story_id(story_id or dialog.entry_story_id)
    story_card = _find_story_card(persona, effective_story_id)
    story_prompt, story_meta = _story_prompt_with_meta(story_card)
    if story_meta:
        memory_context = f"{story_meta} {memory_context}"
    mode_instruction = describe_mode(llm_mode, atmosphere)
    story_instruction = build_story_context(
        story_prompt,
        reentry=bool(story_prompt and message_count > 0),
    )
    feature_states = cache.get("feature_states") or await feature_states_task
    cache["feature_states"] = feature_states
    feature_instruction, feature_mode, feature_max_tokens = build_feature_instruction(feature_states)
    user_message = _build_greeting_user_message(
        llm_mode,
        extra_description,
        story_card=story_card if message_count == 0 else None,
        persona_name=persona.name,
        recent_dialogue=recent_dialogue,
    )
    prompt_ctx = ChatPromptContext(
        persona=persona,
        user=user,
        mode_instruction=mode_instruction,
        memory_short=memory_context,
        memory_long=None,
        story_context=story_instruction,
        recent_dialogue=recent_dialogue,
        story_intro=bool(story_prompt and message_count == 0),
        story_reentry=bool(story_prompt and message_count > 0),
        feature_instruction=feature_instruction,
        feature_mode=feature_mode,
        voice_enabled=False,
        allow_intimate=True,
        soft_block_intimacy=False,
        message_count=message_count,
    )
    messages, _ = build_chat_messages(prompt_ctx, user_message)

    try:
        greeting_text = await simple_chat_completion(messages, max_tokens=feature_max_tokens)
    except Exception as exc:
        logger.error("Failed to generate greeting: %s", exc)
        return None

    session.add(Message(dialog_id=dialog.id, role="assistant", content=greeting_text))
    return GreetingResult(
        text=greeting_text,
        persona_id=persona.id,
        dialog_id=dialog.id,
        mode=greeting_mode,
    )
