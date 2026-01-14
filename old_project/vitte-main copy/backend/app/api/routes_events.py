from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.telegram_webapp import extract_telegram_user_from_request
from ..users_service import get_or_create_user_by_telegram_id
from ..services.analytics import log_event
from ..logging_config import logger

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/miniapp_open")
async def miniapp_open(request: Request, session: AsyncSession = Depends(get_session)):
    """
    Логирует факт открытия Mini App. Telegram ID берём из initData или тела запроса,
    start_param — из тела, если пришёл.
    """
    user = await extract_telegram_user_from_request(request, allow_debug=True)

    payload: dict = {}
    if request.headers.get("content-type", "").lower().startswith("application/json"):
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    start_param = payload.get("start_param")

    if user:
        db_user = await get_or_create_user_by_telegram_id(session, user.id)
        event_payload = {"start_param": start_param} if start_param else {}
        await log_event(session, db_user.id, "miniapp_open", event_payload)
        await session.commit()
        return {"ok": True, "telegram_id_detected": True}

    logger.warning("miniapp_open: telegram user not detected")
    return {"ok": True, "telegram_id_detected": False}
