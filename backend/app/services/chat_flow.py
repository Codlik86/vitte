from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
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
from ..services.memory import collect_recent_memory
from ..story_cards import get_story_cards_for_persona, resolve_story_id, StoryCard
from ..services.features import collect_feature_states, build_feature_instruction
from ..integrations.tts_client import synthesize_voice
from ..services.safety import run_safety_check, SafetyContext, supportive_reply
from ..services.intimacy import evaluate_intimacy
from ..services.prompt_builder import ChatPromptContext, build_chat_messages
from ..services.subscriptions import get_user_subscription_status
from ..services.relationship_state import (
    RelationshipState,
    get_relationship_state,
    save_relationship_state,
    update_relationship_state,
)
from ..services.message_analysis import analyze_message
from ..services.relationship_state import (
    RelationshipState,
    get_relationship_state,
    save_relationship_state,
    update_relationship_state,
)
from ..services.message_analysis import analyze_message


class ChatResult:
    def __init__(
        self,
        reply: str,
        persona_id: int,
        trust_level: int,
        ritual_hint: Optional[str],
        reply_kind: str = "text",
        voice_id: str | None = None,
        voice_url: str | None = None,
        feature_mode: str | None = None,
    ):
        self.reply = reply
        self.persona_id = persona_id
        self.trust_level = trust_level
        self.ritual_hint = ritual_hint
        self.reply_kind = reply_kind
        self.voice_id = voice_id
        self.voice_url = voice_url
        self.feature_mode = feature_mode


class GreetingResult:
    def __init__(self, text: str, persona_id: int, dialog_id: int, mode: str, trust_level: int):
        self.text = text
        self.persona_id = persona_id
        self.dialog_id = dialog_id
        self.mode = mode
        self.trust_level = trust_level


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


def _apply_relationship_deltas(
    state: RelationshipState,
    analysis,
    message_count: int,
) -> RelationshipState:
    trust_delta = 0
    respect_delta = 0
    closeness_delta = 0

    if analysis.is_polite or analysis.shares_feelings:
        trust_delta += 2
        respect_delta += 1
        closeness_delta += 1
    if analysis.is_romantic or analysis.is_flirty:
        trust_delta += 2
        closeness_delta += 3
    if analysis.is_rude:
        trust_delta -= 3
        respect_delta -= 2
        closeness_delta -= 3
    if analysis.is_pushy:
        respect_delta -= 2
        closeness_delta -= 2
    if analysis.asks_for_intimacy and state.closeness_level > 25:
        closeness_delta += 1

    if not analysis.is_rude and not analysis.is_pushy and state.respect_score < 0:
        respect_delta += 1  # мягкое восстановление

    if message_count > 3 and not analysis.is_rude and not analysis.is_pushy:
        closeness_delta += 1
        trust_delta += 1

    return update_relationship_state(
        state,
        trust_delta=trust_delta,
        respect_delta=respect_delta,
        closeness_delta=closeness_delta,
    )


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
    relationship_state: RelationshipState | None,
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
            "Ответь как персонаж, сразу подхвати вводную и атмосферу сцены. "
            "Избегай шаблонных приветствий и режиссёрских ремарок; говори живо и по делу. "
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
    input_text: str,
    *,
    persona_id: int | None = None,
    mode: str = "default",
    atmosphere: str | None = None,
    story_id: str | None = None,
    skip_limits: bool = False,
    skip_increment: bool = False,
) -> ChatResult:
    """
    Общая точка генерации ответа: используется и /api/chat, и ботовым хендлером.
    """
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
    relationship_state = await get_relationship_state(session, user.id, persona.id)

    if not preview_story:
        dialog = await _get_or_create_dialog(session, user, persona, story_id=story_id)
        message_count_result = await session.execute(
            select(func.count(Message.id)).where(Message.dialog_id == dialog.id)
        )
        message_count = message_count_result.scalar_one() or 0
        memory_context = format_memory(await collect_recent_memory(session, dialog, limit=12))
    # история диалога
    effective_story_id = story_id or (dialog.entry_story_id if dialog else None)
    story_card = _find_story_card(persona, effective_story_id)
    story_prompt, story_meta = _story_prompt_with_meta(story_card)
    recent_dialogue = await _recent_dialogue_snippet(session, dialog, limit=12) if dialog and message_count > 0 else None

    analysis = analyze_message(input_text)
    updated_relationship = (
        _apply_relationship_deltas(relationship_state, analysis, message_count)
        if not preview_story
        else relationship_state
    )

    trust_level = updated_relationship.trust_level
    mode_instruction = describe_mode(mode, atmosphere)
    story_instruction = build_story_context(story_prompt)
    if story_meta:
        memory_context = f"{story_meta} {memory_context}"
    ritual_hint = None if preview_story else should_add_ritual(message_count + 1)
    feature_states = collect_feature_states(user)
    feature_instruction, feature_mode, feature_max_tokens = build_feature_instruction(feature_states)

    deep_state = feature_states.get("deep_mode") if feature_states else None
    voice_state = feature_states.get("voice") if feature_states else None
    feature_flags = {
        "has_subscription": access.get("has_subscription", False),
        "deep_mode": bool(getattr(deep_state, "active", False)),
        "closeness_level": updated_relationship.closeness_level,
        "respect_score": updated_relationship.respect_score,
    }
    safety_result = run_safety_check(
        input_text,
        SafetyContext(persona=persona, trust_level=trust_level, message_count=message_count, user_flags=feature_flags),
    )
    intimacy = evaluate_intimacy(
        trust_level=trust_level,
        message_count=message_count,
        user_flags=feature_flags,
    )

    prompt_ctx = ChatPromptContext(
        persona=persona,
        user=user,
        trust_level=trust_level,
        mode_instruction=mode_instruction,
        memory_short=memory_context,
        memory_long=None,
        story_context=story_instruction,
        recent_dialogue=recent_dialogue,
        feature_instruction=feature_instruction,
        feature_mode=feature_mode,
        voice_enabled=bool(getattr(voice_state, "active", False)),
        intimacy_level=intimacy.level,
        intimacy_label=intimacy.label,
        can_engage_intimately=intimacy.can_engage_intimately,
        safety_needs_warmup=safety_result.needs_warmup,
        relationship_state=updated_relationship,
    )
    messages, _ = build_chat_messages(prompt_ctx, input_text)

    if safety_result.is_harm or safety_result.is_illegal:
        reply = supportive_reply(persona)
        logger.info(
            "Safety triggered for user %s persona %s reason=%s",
            user.id,
            persona.id,
            safety_result.reason,
        )
    else:
        reply = await simple_chat_completion(messages, max_tokens=feature_max_tokens)
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
        session.add(Message(dialog_id=dialog.id, role="user", content=input_text))
        session.add(Message(dialog_id=dialog.id, role="assistant", content=reply))
        if not skip_increment and not access.get("has_subscription", False):
            user.free_messages_used += 1
        await save_relationship_state(session, user.id, persona.id, updated_relationship)
        await session.commit()

    return ChatResult(
        reply=reply,
        persona_id=persona.id,
        trust_level=trust_level,
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
    relationship_state = await get_relationship_state(session, user.id, persona.id)
    if message_count is None:
        message_count_result = await session.execute(
            select(func.count(Message.id)).where(Message.dialog_id == dialog.id)
        )
        message_count = message_count_result.scalar_one() or 0

    if message_count == 0:
        greeting_mode = "first"
        llm_mode = "greeting_first"
    elif settings_changed:
        greeting_mode = "updated"
        llm_mode = "greeting_updated"
    else:
        greeting_mode = "return"
        llm_mode = "greeting_return"

    memory_items = await collect_recent_memory(session, dialog, limit=12) if message_count > 0 else []
    memory_context = format_memory(memory_items)
    recent_dialogue = await _recent_dialogue_snippet(session, dialog, limit=12) if message_count > 0 else None
    # история
    effective_story_id = resolve_story_id(story_id or dialog.entry_story_id)
    story_card = _find_story_card(persona, effective_story_id)
    story_prompt, story_meta = _story_prompt_with_meta(story_card)
    if story_meta:
        memory_context = f"{story_meta} {memory_context}"
    trust_level = relationship_state.trust_level
    mode_instruction = describe_mode(llm_mode, atmosphere)
    story_instruction = build_story_context(story_prompt) if message_count == 0 else ""
    feature_states = collect_feature_states(user)
    feature_instruction, feature_mode, feature_max_tokens = build_feature_instruction(feature_states)
    deep_state = feature_states.get("deep_mode") if feature_states else None
    voice_state = feature_states.get("voice") if feature_states else None
    feature_flags = {
        "has_subscription": has_subscription,
        "deep_mode": bool(getattr(deep_state, "active", False)),
        "closeness_level": relationship_state.closeness_level,
        "respect_score": relationship_state.respect_score,
    }
    user_message = _build_greeting_user_message(
        llm_mode,
        extra_description,
        story_card=story_card if message_count == 0 else None,
        persona_name=persona.name,
        recent_dialogue=recent_dialogue,
        relationship_state=relationship_state,
    )
    intimacy = evaluate_intimacy(
        trust_level=trust_level,
        message_count=message_count,
        user_flags=feature_flags,
    )
    prompt_ctx = ChatPromptContext(
        persona=persona,
        user=user,
        trust_level=trust_level,
        mode_instruction=mode_instruction,
        memory_short=memory_context,
        memory_long=None,
        story_context=story_instruction,
        recent_dialogue=recent_dialogue,
        feature_instruction=feature_instruction,
        feature_mode=feature_mode,
        voice_enabled=bool(getattr(voice_state, "active", False)),
        intimacy_level=intimacy.level,
        intimacy_label=intimacy.label,
        can_engage_intimately=intimacy.can_engage_intimately,
        safety_needs_warmup=False,
        relationship_state=relationship_state,
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
        trust_level=trust_level,
    )
