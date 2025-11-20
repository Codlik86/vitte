from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Persona, User
from ..users_service import get_or_create_user_by_telegram_id
from ..integrations.openai_client import simple_chat_completion
from ..schemas import ChatRequest
from ..services.access import build_access_status

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
    persona = await _get_active_persona(session, user)
    access = await build_access_status(session, user)
    if not access["can_send_message"]:
        raise HTTPException(status_code=402, detail="Free limit reached")
    should_update_limit = not access["is_premium"]
    if should_update_limit:
        user.free_messages_used += 1

    system_prompt = persona.system_prompt or ""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.message},
    ]

    try:
        reply = await simple_chat_completion(messages)
    except Exception:
        reply = (
            f"[{persona.name}] {request.message}\n\n"
            "(Это заглушка ответа без обращения к LLM)"
        )

    await session.commit()

    return {"reply": reply, "persona_id": persona.id}
