import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from ..db import get_session
from ..models import Persona, PersonaKind, UserPersona, EventAnalytics, PersonaEventType, Dialog, Message, User
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
from ..logging_config import logger
from ..services.chat_flow import generate_greeting_reply
from ..config import settings
from ..services.telegram_id import get_or_raise_telegram_id
from ..api.miniapp_story_guard import is_miniapp_request, require_story_for_miniapp, validate_story_for_persona
from ..story_cards import resolve_story_id

router = APIRouter(prefix="/api/personas", tags=["personas"])

DEFAULT_SHORT_DESCRIPTION = "Базовый персонаж"
DEFAULT_PERSONA_PHOTO = "/personas/custom-chat.jpg"
CUSTOM_PERSONA_PHOTO = "/personas/custom-chat.jpg"
ALLOWED_DEFAULT_PERSONA_NAMES = (
    "Лина",
    "Марианна",
    "Мей",
    "Стейси",
    "Тая",
    "Юна",
    "Джули",
    "Эш",
    "Ash",
    "Julie",
)
PERSONA_PHOTO_SLUGS = {
    "лина": "lina",
    "марианна": "marianna",
    "аки": "aki",
    "свой герой": "custom",
    "custom": "custom",
    "мей": "mei",
    "стейси": "stacey",
    "тая": "taya",
    "эш": "ash",
    "ash": "ash",
    "джули": "julie",
    "julie": "julie",
    "юна": "yuna",
}
DEFAULT_SLUG = "custom"


def _build_asset_url(path: str) -> str:
    base = settings.miniapp_url.rstrip("/") if settings.miniapp_url else ""
    return f"{base}{path}"


def _story_image_url(card_image: str | None) -> str | None:
    if not card_image:
        return None
    if card_image.startswith("http://") or card_image.startswith("https://"):
        return card_image
    return _build_asset_url(card_image)


def _resolve_persona_photo(persona: Persona) -> str:
    if persona.is_custom:
        return _build_asset_url(CUSTOM_PERSONA_PHOTO)
    key = (persona.name or "").strip().lower()
    slug = PERSONA_PHOTO_SLUGS.get(key, DEFAULT_SLUG)
    return build_persona_asset_url("chat", slug)


def build_persona_asset_url(kind: str, slug: str, story_key: str | None = None) -> str:
    if kind == "chat":
        return _build_asset_url(f"/personas/{slug}-chat.jpg")
    if kind == "card":
        return _build_asset_url(f"/personas/{slug}-card.jpg")
    if kind == "story" and story_key:
        return _build_asset_url(f"/personas/{slug}-story-{story_key}.jpg")
    return _build_asset_url(DEFAULT_PERSONA_PHOTO)


def _resolve_persona_slug(persona: Persona) -> str:
    if persona.is_custom:
        return DEFAULT_SLUG
    key = (persona.name or "").strip().lower()
    return PERSONA_PHOTO_SLUGS.get(key, DEFAULT_SLUG)


def _build_custom_key(user_id: int) -> str:
    return f"custom_{user_id}_{uuid4().hex[:8]}"


def _build_short_description(persona: Persona) -> str:
    return persona.short_description or DEFAULT_SHORT_DESCRIPTION


def _build_list_item(persona: Persona, user_id: int | None, active_id: int | None) -> PersonaListItem:
    slug = _resolve_persona_slug(persona)
    avatar_chat = build_persona_asset_url("chat", slug)
    avatar_card = build_persona_asset_url("card", slug)
    kind_value = None
    if hasattr(persona, "kind"):
        kind_raw = persona.kind
        if isinstance(kind_raw, str):
            kind_value = kind_raw
        else:
            try:
                kind_value = kind_raw.value  # type: ignore[attr-defined]
            except Exception:
                kind_value = None
    return PersonaListItem(
        id=persona.id,
        name=persona.name,
        short_title=persona.short_title or persona.short_description or persona.name,
        gender=getattr(persona, "gender", None),
        kind=kind_value,
        short_description=_build_short_description(persona),
        is_default=bool(persona.is_default),
        is_owner=bool(user_id is not None and persona.owner_user_id == user_id),
        is_selected=bool(active_id is not None and persona.id == active_id),
        is_custom=bool(persona.is_custom),
        avatar_url=avatar_chat,
        avatar_chat_url=avatar_chat,
        avatar_card_url=avatar_card,
    )


def _build_details(
    persona: Persona,
    user_id: int | None,
    active_id: int | None,
    dialog_info: tuple[Dialog | None, int] | None = None,
) -> PersonaDetails:
    item = _build_list_item(persona, user_id, active_id)
    slug = _resolve_persona_slug(persona)
    story_cards = [
        {
            "id": card.id,
            "key": card.key,
            "title": card.title,
            "description": card.description,
            "atmosphere": card.atmosphere,
            "prompt": card.prompt,
            "image": build_persona_asset_url("story", slug, card.key) if card.image else None,
        }
        for card in get_story_cards_for_persona(persona.archetype, persona.name)
    ]
    dialog_obj = None
    has_history = False
    if dialog_info:
        dialog_obj, message_count = dialog_info
        has_history = bool(message_count > 0)
    return PersonaDetails(
        **item.model_dump(),
        long_description=persona.long_description,
        archetype=persona.archetype,
        legend_full=persona.legend_full or _combine_legend_response(persona),
        emotions_full=persona.emotions_full or _combine_emotions_response(persona),
        triggers_positive=persona.triggers_positive,
        triggers_negative=persona.triggers_negative,
        story_cards=story_cards,
        has_history=has_history,
        dialog_id=dialog_obj.id if dialog_obj else None,
    )


def _is_persona_owned_or_default(persona: Persona, user_id: int) -> bool:
    return persona.is_default or persona.owner_user_id == user_id


async def _get_dialog_info(
    session: AsyncSession, user_id: int, persona_id: int
) -> tuple[Dialog | None, int]:
    stmt = (
        select(Dialog)
        .where(Dialog.user_id == user_id, Dialog.character_id == persona_id)
        .order_by(Dialog.created_at.desc())
    )
    result = await session.execute(stmt)
    dialog = result.scalars().first()
    if dialog is None:
        return None, 0
    msg_count_stmt = select(func.count(Message.id)).where(Message.dialog_id == dialog.id)
    msg_count_res = await session.execute(msg_count_stmt)
    return dialog, msg_count_res.scalar_one() or 0


@router.get("", response_model=PersonasListResponse)
async def list_personas(
    request: Request,
    telegram_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    debug_personas = os.getenv("DEBUG_PERSONAS") == "1"
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    defaults_result = await session.execute(select(Persona).where(Persona.is_default.is_(True)))
    default_personas = defaults_result.scalars().all()
    active_defaults = [p for p in default_personas if p.is_active]
    allowed_set = {name.strip() for name in ALLOWED_DEFAULT_PERSONA_NAMES}
    allowed_lower = {name.lower() for name in allowed_set}
    blocked: list[tuple[int, str, str]] = []
    for p in active_defaults:
        normalized = (p.name or "").strip().lower()
        if normalized not in allowed_lower:
            blocked.append((p.id, p.name or "", "name_not_allowed"))
    if debug_personas:
        logger.info(
            "personas.list debug telegram_id=%s defaults_total=%s active_defaults=%s blocked=%s allowed=%s",
            telegram_id,
            len(default_personas),
            len(active_defaults),
            blocked,
            sorted(allowed_set),
        )

    result = await session.execute(
        select(Persona).where(
            (
                (Persona.is_active.is_(True))
                & (Persona.is_default.is_(True))
            )
            | (Persona.owner_user_id == user.id)
        ).order_by(Persona.id)
    )
    personas = result.scalars().all()
    if debug_personas:
        ash_present = any((p.name or "").strip().lower() == "ash" for p in personas)
        julie_present = any((p.name or "").strip().lower() == "julie" for p in personas)
        ash_db = any((p.name or "").strip().lower() == "ash" for p in default_personas)
        julie_db = any((p.name or "").strip().lower() == "julie" for p in default_personas)
        logger.info(
            "personas.list result count=%s user_owned=%s ash=%s julie=%s ash_db=%s julie_db=%s personas=%s allowlist=%s",
            len(personas),
            len([p for p in personas if p.owner_user_id == user.id]),
            ash_present,
            julie_present,
            ash_db,
            julie_db,
            [(p.id, p.name, p.is_active, p.is_default) for p in personas],
            sorted(allowed_set),
        )

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
    request: Request,
    telegram_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id, allow_debug=False)
    user = None
    if telegram_id:
        user = await get_or_create_user_by_telegram_id(session, telegram_id)
    result = await session.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    normalized_name = (persona.name or "").strip().lower()
    allowed_lower = {name.lower() for name in ALLOWED_DEFAULT_PERSONA_NAMES}
    if persona.is_default and (not persona.is_active or normalized_name not in allowed_lower):
        raise HTTPException(status_code=404, detail="Persona not available")

    user_id = user.id if user else None
    active_id = user.active_persona_id if user else None
    dialog_info = None
    if user:
        dialog_info = await _get_dialog_info(session, user.id, persona.id)
    return _build_details(persona, user_id, active_id, dialog_info)


@router.post("/{persona_id}/select", response_model=PersonaDetails)
async def select_persona(
    persona_id: int,
    request: Request,
    telegram_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    persona_result = await session.execute(
        select(Persona).where(Persona.id == persona_id)
    )
    persona = persona_result.scalar_one_or_none()
    normalized_name = (persona.name or "").strip().lower() if persona else ""
    allowed_lower = {name.lower() for name in ALLOWED_DEFAULT_PERSONA_NAMES}
    if (
        persona is None
        or (persona.is_default and (not persona.is_active or normalized_name not in allowed_lower))
        or not _is_persona_owned_or_default(persona, user.id)
    ):
        raise HTTPException(status_code=404, detail="Persona not found")

    await _apply_persona_selection(session, user, persona)
    await session.commit()
    dialog_info = await _get_dialog_info(session, user.id, persona.id)
    return _build_details(persona, user.id, user.active_persona_id, dialog_info)


@router.post("/select_and_greet", response_model=PersonaSelectResponse)
async def select_persona_and_greet(
    payload: PersonaSelectRequest,
    request: Request,
    telegram_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    if is_miniapp_request(request):
        require_story_for_miniapp(request, payload.story_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    persona_result = await session.execute(
        select(Persona).where(Persona.id == payload.persona_id)
    )
    persona = persona_result.scalar_one_or_none()
    normalized_name = (persona.name or "").strip().lower() if persona else ""
    allowed_lower = {name.lower() for name in ALLOWED_DEFAULT_PERSONA_NAMES}
    if (
        persona is None
        or (persona.is_default and (not persona.is_active or normalized_name not in allowed_lower))
        or not _is_persona_owned_or_default(persona, user.id)
    ):
        raise HTTPException(status_code=404, detail="Persona not found")

    resolved_story_id = resolve_story_id(payload.story_id)
    if is_miniapp_request(request):
        resolved_story_id = validate_story_for_persona(persona, payload.story_id)

    await _apply_persona_selection(session, user, persona)
    access = await build_access_status(session, user)

    greeting_sent = False
    dialog_id: int | None = None
    greeting_mode: str | None = None
    dialog_info = await _get_dialog_info(session, user.id, persona.id)

    if payload.send_greeting:
        dialog, message_count = dialog_info
        if dialog is None:
            dialog = await _get_or_create_dialog(session, user, persona, resolved_story_id)
            dialog_info = (dialog, 0)
            message_count = 0
        dialog_id = dialog.id
        greeting = await generate_greeting_reply(
            session=session,
            user=user,
            persona=persona,
            dialog=dialog,
            message_count=message_count,
            has_subscription=bool(access.get("has_subscription")),
            atmosphere=payload.atmosphere,
            story_id=resolved_story_id,
            extra_description=payload.extra_description,
            settings_changed=payload.settings_changed,
        )
        if greeting:
            greeting_mode = greeting.mode
            photo = _resolve_persona_photo(persona)
            try:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=photo,
                    caption=greeting.text,
                )
                greeting_sent = True
            except Exception as exc:
                logger.error("Failed to send greeting photo: %s", exc)
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=greeting.text)
                    greeting_sent = True
                except Exception as exc2:
                    logger.error("Failed to send greeting fallback message: %s", exc2)

    await session.commit()
    return PersonaSelectResponse(
        ok=True,
        persona_id=persona.id,
        dialog_id=dialog_id,
        greeting_sent=greeting_sent,
        greeting_mode=greeting_mode,
    )


@router.post("/custom", response_model=PersonaDetails)
async def create_custom_persona(
    payload: PersonaCustomCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    access = await build_access_status(session, user)
    if not access.get("has_subscription"):
        raise HTTPException(status_code=403, detail="Custom personas доступны в Premium")
    vibe = (payload.vibe or "").strip()
    vibe_sentence = f" Доп. детали: {vibe}." if vibe else ""
    short_title = payload.short_description or payload.name
    gender = (payload.gender or "female").strip() or "female"

    existing = await session.execute(
        select(Persona).where(Persona.owner_user_id == user.id, Persona.is_custom.is_(True))
    )
    existing_persona = existing.scalars().first()
    if existing_persona and not payload.replace_existing:
        raise HTTPException(status_code=409, detail="custom_persona_exists")

    target_persona = existing_persona or Persona(owner_user_id=user.id)
    target_persona.name = payload.name
    target_persona.short_title = short_title
    target_persona.short_description = payload.short_description
    target_persona.gender = gender
    target_persona.kind = PersonaKind.CUSTOM
    target_persona.long_description = vibe or None
    target_persona.description_short = short_title
    target_persona.description_long = vibe or payload.short_description
    target_persona.archetype = "custom"
    target_persona.system_prompt = (
        "Ты романтический AI-компаньон. Вайб: "
        f"{payload.short_description}. Ты говоришь по-русски, мягко, с флиртом и эмпатией."
        f"{vibe_sentence}"
    )
    target_persona.key = target_persona.key or _build_custom_key(user.id)
    target_persona.is_default = False
    target_persona.is_custom = True
    target_persona.is_active = True
    target_persona.owner_user_id = user.id
    target_persona.created_by_user_id = user.id
    target_persona.short_lore = vibe or payload.short_description
    target_persona.background = None
    target_persona.legend_full = target_persona.short_lore
    target_persona.emotional_style = "Ты мягкая версия кастомного героя"
    target_persona.relationship_style = "Ты подстраиваешься под автора образа"
    target_persona.emotions_full = (
        f"{target_persona.emotional_style}. {target_persona.relationship_style}."
    )
    target_persona.style_tags = []
    target_persona.hooks = []
    target_persona.triggers_positive = []
    target_persona.triggers_negative = []

    session.add(target_persona)
    await session.flush()

    link_result = await session.execute(
        select(UserPersona).where(
            UserPersona.user_id == user.id,
            UserPersona.persona_id == target_persona.id,
        )
    )
    link = link_result.scalar_one_or_none()
    if link is None:
        link = UserPersona(
            user_id=user.id,
            persona_id=target_persona.id,
            is_owner=True,
            is_favorite=True,
        )
        session.add(link)
    else:
        link.is_owner = True

    user.active_persona_id = target_persona.id

    ev = EventAnalytics(
        user_id=user.id,
        event_type="persona_custom_created",
        payload={"persona_id": target_persona.id, "name": target_persona.name},
    )
    session.add(ev)

    await log_persona_event(
        session,
        user_id=user.id,
        persona_id=target_persona.id,
        event_type=PersonaEventType.PERSONA_CUSTOMIZED,
    )

    await session.commit()
    dialog_info = await _get_dialog_info(session, user.id, target_persona.id)
    return _build_details(target_persona, user.id, user.active_persona_id, dialog_info)


def _combine_legend_response(persona: Persona) -> str | None:
    parts = [persona.short_lore, persona.background]
    combined = " ".join([p.strip() for p in parts if p])
    return combined or None


def _combine_emotions_response(persona: Persona) -> str | None:
    parts = [persona.emotional_style, persona.relationship_style]
    combined = " ".join([p.strip() for p in parts if p])
    return combined or None


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


async def _get_or_create_dialog(
    session: AsyncSession, user: User, persona: Persona, story_id: str | None = None
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
