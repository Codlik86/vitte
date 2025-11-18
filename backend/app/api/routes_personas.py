from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, UserPersona, EventAnalytics, PersonaEventType
from ..users_service import get_or_create_user_by_telegram_id
from ..schemas import (
    PersonasListResponse,
    PersonaSelectRequest,
    PersonaCustomCreateRequest,
)
from ..services.persona_events import log_persona_event

router = APIRouter(prefix="/api/personas", tags=["personas"])


def persona_to_dict(persona: Persona, is_active: bool = False) -> dict:
    return {
        "id": persona.id,
        "name": persona.name,
        "short_description": persona.short_description,
        "archetype": persona.archetype,
        "is_default": bool(persona.is_default),
        "is_custom": not bool(persona.is_default),
        "is_active": is_active,
    }


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

    items = [persona_to_dict(p, is_active=(p.id == user.active_persona_id)) for p in personas]
    await log_persona_event(
        session,
        user_id=user.id,
        persona_id=None,
        event_type=PersonaEventType.CATALOG_OPENED,
    )
    await session.commit()
    return PersonasListResponse(items=items)


@router.post("/select")
async def select_persona(
    payload: PersonaSelectRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)

    persona_result = await session.execute(
        select(Persona).where(Persona.id == payload.persona_id)
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
        up = UserPersona(user_id=user.id, persona_id=persona.id, is_favorite=True)
        session.add(up)

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
    return {"ok": True}


@router.post("/custom")
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

    link = UserPersona(user_id=user.id, persona_id=persona.id, is_favorite=True)
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
    return {"ok": True}
