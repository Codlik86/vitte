from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, User, Dialog, Message
from ..users_service import get_or_create_user_by_telegram_id
from ..integrations.openai_client import simple_chat_completion
from ..schemas import ChatRequest, ChatResponse
from ..services.access import build_access_status
from ..services.llm_adapter import (
    compose_messages,
    calculate_trust_level,
    describe_mode,
    build_story_context,
    should_add_ritual,
    format_memory,
)
from ..services.memory import collect_recent_memory
from ..story_cards import get_story_cards_for_persona

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
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_session)):
    user = await get_or_create_user_by_telegram_id(session, request.telegram_id)
    persona = await _resolve_persona(session, user, request)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    preview_story = request.mode == "story" and request.persona_id is not None

    access = await build_access_status(session, user)
    if not preview_story and not access["can_send_message"]:
        raise HTTPException(status_code=402, detail="Free limit reached")

    dialog: Dialog | None = None
    message_count = 0
    memory_context = "Нет особых воспоминаний, но персонаж открыт к новым."

    if not preview_story:
        dialog = await _get_or_create_dialog(session, user, persona)
        message_count_result = await session.execute(
            select(func.count(Message.id)).where(Message.dialog_id == dialog.id)
        )
        message_count = message_count_result.scalar_one() or 0
        memory_context = format_memory(await collect_recent_memory(session, dialog))

    trust_level = calculate_trust_level(message_count, access["has_subscription"])
    mode_instruction = describe_mode(request.mode, request.atmosphere)
    story_prompt = None
    if request.story_id:
        for card in get_story_cards_for_persona(persona.archetype, persona.name):
            if card.id == request.story_id:
                story_prompt = card.prompt
                break
    story_instruction = build_story_context(story_prompt)
    ritual_hint = None if preview_story else should_add_ritual(message_count + 1)
    messages, _ = compose_messages(
        persona,
        user,
        user_message=request.message,
        trust_level=trust_level,
        has_subscription=access["has_subscription"],
        age_confirmed=user.age_confirmed,
        memory_context=memory_context,
        mode_instruction=mode_instruction,
        story_instruction=story_instruction,
        ritual_hint=ritual_hint,
    )

    reply = await simple_chat_completion(messages)

    if not preview_story and dialog:
        session.add(Message(dialog_id=dialog.id, role="user", content=request.message))
        session.add(Message(dialog_id=dialog.id, role="assistant", content=reply))
        if not access["has_subscription"]:
            user.free_messages_used += 1
        await session.commit()

    return ChatResponse(
        reply=reply,
        persona_id=persona.id,
        trust_level=trust_level,
        ritual_hint=ritual_hint,
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


async def _resolve_persona(session: AsyncSession, user: User, request: ChatRequest) -> Persona | None:
    if request.persona_id:
        result = await session.execute(select(Persona).where(Persona.id == request.persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            return persona
    return await _get_active_persona(session, user)
