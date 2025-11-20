from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, UserPersona, EventAnalytics, PersonaEventType, Dialog, Message, User
from ..users_service import get_or_create_user_by_telegram_id
from ..schemas import (
    PersonasListResponse,
    PersonaCustomCreateRequest,
    PersonaListItem,
    PersonaDetails,
    PersonaSelectRequest,
    PersonaSelectResponse,
)
from ..services.persona_events import log_persona_event
from ..services.access import build_access_status
from ..story_cards import get_story_cards_for_persona
from ..bot import bot
from ..integrations.openai_client import simple_chat_completion
from ..logging_config import logger
from ..services.llm_adapter import (
    compose_messages,
    calculate_trust_level,
    describe_mode,
    build_story_context,
    format_memory,
)

router = APIRouter(prefix="/api/personas", tags=["personas"])

DEFAULT_SHORT_DESCRIPTION = "Базовый персонаж"


def _build_short_description(persona: Persona) -> str:
    return persona.short_description or DEFAULT_SHORT_DESCRIPTION


def _build_list_item(persona: Persona, user_id: int | None, active_id: int | None) -> PersonaListItem:
    return PersonaListItem(
        id=persona.id,
        name=persona.name,
        short_description=_build_short_description(persona),
        is_default=bool(persona.is_default),
        is_owner=bool(user_id is not None and persona.owner_user_id == user_id),
        is_selected=bool(active_id is not None and persona.id == active_id),
    )


def _build_details(persona: Persona, user_id: int | None, active_id: int | None) -> PersonaDetails:
    item = _build_list_item(persona, user_id, active_id)
    story_cards = [
        {
            "id": card.id,
            "title": card.title,
            "description": card.description,
            "atmosphere": card.atmosphere,
            "prompt": card.prompt,
        }
        for card in get_story_cards_for_persona(persona.archetype, persona.name)
    ]
    return PersonaDetails(
        **item.model_dump(),
        long_description=persona.long_description,
        archetype=persona.archetype,
        short_lore=persona.short_lore,
        background=persona.background,
        emotional_style=persona.emotional_style,
        relationship_style=persona.relationship_style,
        hooks=persona.hooks,
        triggers_positive=persona.triggers_positive,
        triggers_negative=persona.triggers_negative,
        story_cards=story_cards,
    )


def _is_persona_owned_or_default(persona: Persona, user_id: int) -> bool:
    return persona.is_default or persona.owner_user_id == user_id


@router.get("", response_model=PersonasListResponse)
async def list_personas(
    telegram_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    result = await session.execute(
        select(Persona).where(
            (Persona.is_default.is_(True)) | (Persona.owner_user_id == user.id)
        ).order_by(Persona.id)
    )
    personas = result.scalars().all()

    items = [
        _build_list_item(p, user.id, user.active_persona_id)
        for p in personas
    ]
    await log_persona_event(
        session,
        user_id=user.id,
        persona_id=None,
        event_type=PersonaEventType.CATALOG_OPENED,
    )
    await session.commit()
    return PersonasListResponse(items=items)


@router.get("/{persona_id}", response_model=PersonaDetails)
async def get_persona(
    persona_id: int,
    telegram_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    user = None
    if telegram_id:
        user = await get_or_create_user_by_telegram_id(session, telegram_id)
    result = await session.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    user_id = user.id if user else None
    active_id = user.active_persona_id if user else None
    return _build_details(persona, user_id, active_id)


@router.post("/{persona_id}/select", response_model=PersonaDetails)
async def select_persona(
    persona_id: int,
    telegram_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    persona_result = await session.execute(
        select(Persona).where(Persona.id == persona_id)
    )
    persona = persona_result.scalar_one_or_none()
    if persona is None or not _is_persona_owned_or_default(persona, user.id):
        raise HTTPException(status_code=404, detail="Persona not found")

    await _apply_persona_selection(session, user, persona)
    await session.commit()
    return _build_details(persona, user.id, user.active_persona_id)


@router.post("/select_and_greet", response_model=PersonaSelectResponse)
async def select_persona_and_greet(
    payload: PersonaSelectRequest,
    telegram_id: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    persona_result = await session.execute(
        select(Persona).where(Persona.id == payload.persona_id)
    )
    persona = persona_result.scalar_one_or_none()
    if persona is None or not _is_persona_owned_or_default(persona, user.id):
        raise HTTPException(status_code=404, detail="Persona not found")

    await _apply_persona_selection(session, user, persona)
    access = await build_access_status(session, user)

    greeting_sent = False
    dialog_id: int | None = None

    if payload.send_greeting:
        dialog = await _get_or_create_dialog(session, user, persona)
        dialog_id = dialog.id
        greeting_text = await _prepare_greeting_message(
            session=session,
            user=user,
            persona=persona,
            dialog=dialog,
            has_subscription=bool(access.get("has_subscription")),
            extra_description=payload.extra_description,
        )
        if greeting_text:
            try:
                await bot.send_message(chat_id=user.telegram_id, text=greeting_text)
                greeting_sent = True
            except Exception as exc:
                logger.error("Failed to send greeting message: %s", exc)

    await session.commit()
    return PersonaSelectResponse(
        ok=True,
        persona_id=persona.id,
        dialog_id=dialog_id,
        greeting_sent=greeting_sent,
    )


@router.post("/custom", response_model=PersonaDetails)
async def create_custom_persona(
    payload: PersonaCustomCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)
    access = await build_access_status(session, user)
    if not access.get("has_subscription"):
        raise HTTPException(status_code=403, detail="Custom personas доступны в Premium")
    vibe = (payload.vibe or "").strip()
    vibe_sentence = f" Доп. детали: {vibe}." if vibe else ""

    persona = Persona(
        name=payload.name,
        short_description=payload.short_description,
        long_description=vibe or None,
        archetype="custom",
        system_prompt=(
            "Ты романтический AI-компаньон. Вайб: "
            f"{payload.short_description}. Ты говоришь по-русски, мягко, с флиртом и эмпатией."
            f"{vibe_sentence}"
        ),
        is_default=False,
        is_custom=True,
        is_active=True,
        owner_user_id=user.id,
        short_lore=vibe or payload.short_description,
        background=None,
        emotional_style="Ты мягкая версия кастомного героя",
        relationship_style="Ты подстраиваешься под автора образа",
        hooks=None,
        triggers_positive=None,
        triggers_negative=None,
    )
    session.add(persona)
    await session.flush()

    link = UserPersona(
        user_id=user.id,
        persona_id=persona.id,
        is_owner=True,
        is_favorite=True,
    )
    session.add(link)

    user.active_persona_id = persona.id

    ev = EventAnalytics(
        user_id=user.id,
        event_type="persona_custom_created",
        payload={"persona_id": persona.id, "name": persona.name},
    )
    session.add(ev)

    await log_persona_event(
        session,
        user_id=user.id,
        persona_id=persona.id,
        event_type=PersonaEventType.PERSONA_CUSTOMIZED,
    )

    await session.commit()
    return _build_details(persona, user.id, user.active_persona_id)


async def _apply_persona_selection(session: AsyncSession, user: User, persona: Persona) -> None:
    user.active_persona_id = persona.id
    up_result = await session.execute(
        select(UserPersona).where(
            UserPersona.user_id == user.id,
            UserPersona.persona_id == persona.id,
        )
    )
    up = up_result.scalar_one_or_none()
    if up is None:
        up = UserPersona(
            user_id=user.id,
            persona_id=persona.id,
            is_owner=bool(persona.owner_user_id == user.id),
            is_favorite=True,
        )
        session.add(up)
    else:
        up.is_owner = bool(persona.owner_user_id == user.id)

    ev = EventAnalytics(
        user_id=user.id,
        event_type="persona_selected",
        payload={"persona_id": persona.id, "archetype": persona.archetype},
    )
    session.add(ev)
    await log_persona_event(
        session,
        user_id=user.id,
        persona_id=persona.id,
        event_type=PersonaEventType.PERSONA_SELECTED,
    )


async def _get_or_create_dialog(session: AsyncSession, user: User, persona: Persona) -> Dialog:
    stmt = (
        select(Dialog)
        .where(Dialog.user_id == user.id, Dialog.character_id == persona.id)
        .order_by(Dialog.created_at.desc())
    )
    result = await session.execute(stmt)
    dialog = result.scalars().first()
    if dialog:
        return dialog
    dialog = Dialog(user_id=user.id, character_id=persona.id)
    session.add(dialog)
    await session.flush()
    return dialog


async def _prepare_greeting_message(
    *,
    session: AsyncSession,
    user: User,
    persona: Persona,
    dialog: Dialog,
    has_subscription: bool,
    extra_description: str | None,
) -> str | None:
    count_stmt = select(func.count(Message.id)).where(Message.dialog_id == dialog.id)
    count_result = await session.execute(count_stmt)
    if (count_result.scalar_one() or 0) > 0:
        return None

    trust_level = calculate_trust_level(0, has_subscription)
    memory_context = format_memory([])
    mode_instruction = describe_mode("first_message", None)
    story_instruction = ""
    prompt_extra = (
        f"Дополнительный контекст от пользователя: {extra_description.strip()}."
        if extra_description
        else ""
    )
    user_message = (
        "Сформируй первое приветствие для пользователя. Представься от имени персонажа, "
        "поддержи тёплую атмосферу, задай один безопасный вопрос и пригласи продолжить диалог. "
        "Не упоминай, что получил инструкцию. "
        f"{prompt_extra}"
    ).strip()

    messages, _ = compose_messages(
        persona,
        user,
        user_message=user_message,
        trust_level=trust_level,
        has_subscription=has_subscription,
        age_confirmed=user.age_confirmed,
        memory_context=memory_context,
        mode_instruction=mode_instruction,
        story_instruction=story_instruction,
        ritual_hint=None,
    )

    try:
        greeting = await simple_chat_completion(messages)
    except Exception as exc:
        logger.error("Failed to generate greeting: %s", exc)
        return None

    session.add(Message(dialog_id=dialog.id, role="assistant", content=greeting))
    return greeting
