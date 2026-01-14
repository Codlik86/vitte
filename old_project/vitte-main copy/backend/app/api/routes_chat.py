from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, User, Dialog, Message
from ..users_service import get_or_create_user_by_telegram_id
from ..schemas import ChatRequest, ChatResponse
from ..services.chat_flow import generate_chat_reply
from ..services.telegram_id import get_or_raise_telegram_id
from ..api.miniapp_story_guard import is_miniapp_request, require_story_for_miniapp, validate_story_for_persona
from ..story_cards import resolve_story_id

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _get_active_persona(session: AsyncSession, user: User) -> Persona:
    if user.active_persona_id:
        p_res = await session.execute(
            select(Persona).where(Persona.id == user.active_persona_id)
        )
        persona = p_res.scalar_one_or_none()
        if persona:
            return persona

    res = await session.execute(
        select(Persona).where(Persona.is_default.is_(True)).order_by(Persona.id)
    )
    persona = res.scalar_one_or_none()
    if persona:
        return persona
    raise HTTPException(status_code=404, detail="No personas available")


@router.post("")
async def chat(payload: ChatRequest, request: Request, session: AsyncSession = Depends(get_session)):
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    resolved_story_id = payload.story_id
    if is_miniapp_request(request):
        require_story_for_miniapp(request, payload.story_id)
        if payload.persona_id is None:
            raise HTTPException(status_code=400, detail="persona_required")
        persona_check = await session.execute(select(Persona).where(Persona.id == payload.persona_id))
        persona = persona_check.scalar_one_or_none()
        if persona is None:
            raise HTTPException(status_code=404, detail="Persona not found")
        resolved_story_id = validate_story_for_persona(persona, payload.story_id)
    else:
        resolved_story_id = resolve_story_id(payload.story_id)

    try:
        result = await generate_chat_reply(
            session=session,
            user=user,
            input_text=payload.message,
            persona_id=payload.persona_id,
            mode=payload.mode or "default",
            atmosphere=payload.atmosphere,
            story_id=resolved_story_id,
            skip_limits=False,
            skip_increment=False,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return ChatResponse(
        reply=result.reply,
        persona_id=result.persona_id,
        ritual_hint=result.ritual_hint,
        reply_kind=result.reply_kind,
        voice_id=result.voice_id,
        voice_url=result.voice_url,
        feature_mode=result.feature_mode,
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


async def _resolve_persona(session: AsyncSession, user: User, persona_id: int | None) -> Persona | None:
    if persona_id:
        result = await session.execute(select(Persona).where(Persona.id == persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            return persona
    return await _get_active_persona(session, user)
