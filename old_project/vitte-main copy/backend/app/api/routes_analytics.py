from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..schemas import AnalyticsEventRequest
from ..services.analytics import log_event
from ..users_service import get_or_create_user_by_telegram_id

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/events")
async def create_event(
    payload: AnalyticsEventRequest,
    session: AsyncSession = Depends(get_session),
):
    user_id: int | None = None
    if payload.telegram_id:
        user = await get_or_create_user_by_telegram_id(session, payload.telegram_id)
        user_id = user.id
    await log_event(session, user_id, payload.event_type, payload.payload or {})
    await session.commit()
    return {"ok": True}
