from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.telegram_id import get_or_raise_telegram_id
from ..users_service import get_or_create_user_by_telegram_id
from ..services.analytics import log_event

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/miniapp_open")
async def miniapp_open(request: Request, session: AsyncSession = Depends(get_session)):
    """
    Логирует факт открытия Mini App. Telegram ID берём из initData или тела запроса,
    start_param — из тела, если пришёл.
    """
    telegram_id = await get_or_raise_telegram_id(request)

    payload: dict = {}
    if request.headers.get("content-type", "").lower().startswith("application/json"):
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    start_param = payload.get("start_param")

    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    event_payload = {"start_param": start_param} if start_param else {}
    await log_event(session, user.id, "miniapp_open", event_payload)
    await session.commit()

    return {"ok": True}
