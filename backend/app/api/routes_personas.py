from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, UserPersona, EventAnalytics, PersonaKind
from ..users_service import get_or_create_user_by_telegram_id

router = APIRouter(prefix="/api/personas", tags=["personas"])


def persona_to_dict(persona: Persona, is_selected: bool = False) -> dict:
    return {
        "id": persona.id,
        "key": persona.key,
        "name": persona.name,
        "short_title": persona.short_title,
        "gender": persona.gender,
        "kind": persona.kind,
        "description_short": persona.description_short,
        "description_long": persona.description_long,
        "style_tags": persona.style_tags or {},
        "is_custom": persona.is_custom,
        "is_selected": is_selected,
    }


@router.get("")
async def list_personas(
    telegram_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Persona).where(Persona.is_active.is_(True)).order_by(Persona.id)
    )
    personas = result.scalars().all()

    user = None
    active_id: int | None = None
    if telegram_id is not None:
        user = await get_or_create_user_by_telegram_id(session, telegram_id)
        active_id = user.active_persona_id

    data = [persona_to_dict(p, is_selected=(p.id == active_id)) for p in personas]
    return {"items": data}


@router.get("/{persona_id}")
async def get_persona(
    persona_id: int,
    telegram_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Persona).where(Persona.id == persona_id, Persona.is_active.is_(True)))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    active_id: int | None = None
    if telegram_id is not None:
        user = await get_or_create_user_by_telegram_id(session, telegram_id)
        active_id = user.active_persona_id

    return persona_to_dict(persona, is_selected=(persona.id == active_id))


@router.post("/select")
async def select_persona(
    telegram_id: int = Query(...),
    persona_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Persona).where(Persona.id == persona_id, Persona.is_active.is_(True)))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    user.active_persona_id = persona.id

    up_result = await session.execute(
        select(UserPersona).where(
            UserPersona.user_id == user.id,
            UserPersona.persona_id == persona.id,
        )
    )
    up = up_result.scalar_one_or_none()
    if up is None:
        up = UserPersona(user_id=user.id, persona_id=persona.id, is_owner=False, is_favorite=True)
        session.add(up)

    ev = EventAnalytics(
        user_id=user.id,
        event_type="persona_selected",
        payload={"persona_id": persona.id, "persona_key": persona.key},
    )
    session.add(ev)

    await session.commit()

    return {"ok": True, "active_persona_id": persona.id}


@router.post("/custom")
async def create_custom_persona(
    telegram_id: int = Query(...),
    name: str = Query(..., max_length=64),
    short_title: str = Query(..., max_length=128),
    description_short: str = Query(..., max_length=256),
    style: str = Query("custom"),
    session: AsyncSession = Depends(get_session),
):
    """
    Простейший API для создания кастомного персонажа.
    В следующих этапах можно будет заменить на полноценный body JSON.
    """
    user = await get_or_create_user_by_telegram_id(session, telegram_id)

    persona = Persona(
        key=f"custom_{user.id}",
        name=name,
        short_title=short_title,
        gender="nb",
        kind=PersonaKind.SOFT_EMPATH,
        description_short=description_short,
        description_long=description_short,
        style_tags={"style": style, "custom": True},
        is_active=True,
        is_custom=True,
        created_by_user_id=user.id,
    )
    session.add(persona)
    await session.flush()

    up = UserPersona(
        user_id=user.id,
        persona_id=persona.id,
        is_owner=True,
        is_favorite=True,
    )
    session.add(up)

    user.active_persona_id = persona.id

    ev = EventAnalytics(
        user_id=user.id,
        event_type="persona_custom_created",
        payload={"persona_id": persona.id},
    )
    session.add(ev)

    await session.commit()

    return {"ok": True, "persona": persona_to_dict(persona, is_selected=True)}
