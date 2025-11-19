from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, UserPersona, EventAnalytics, PersonaEventType
from ..users_service import get_or_create_user_by_telegram_id
from ..schemas import (
    PersonasListResponse,
    PersonaCustomCreateRequest,
    PersonaListItem,
    PersonaDetails,
)
from ..services.persona_events import log_persona_event

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
    return PersonaDetails(
        **item.model_dump(),
        long_description=persona.long_description,
        archetype=persona.archetype,
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

    await session.commit()
    return _build_details(persona, user.id, user.active_persona_id)


@router.post("/custom", response_model=PersonaDetails)
async def create_custom_persona(
    payload: PersonaCustomCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)

    persona = Persona(
        name=payload.name,
        short_description=payload.short_description,
        long_description=None,
        archetype="custom",
        system_prompt=(
            "Ты романтический AI-компаньон. Вайб: "
            f"{payload.short_description}. Ты говоришь по-русски, мягко, с флиртом и эмпатией."
        ),
        is_default=False,
        is_custom=True,
        is_active=True,
        owner_user_id=user.id,
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
