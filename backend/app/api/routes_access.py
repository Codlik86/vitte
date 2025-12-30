import os

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..users_service import get_or_create_user_by_telegram_id
from ..services.access import build_access_status
from ..schemas import AccessStatusResponse
from ..services.telegram_id import get_or_raise_telegram_id
from ..logging_config import logger

router = APIRouter(prefix="/api/access", tags=["access"])


@router.get("/status", response_model=AccessStatusResponse)
async def access_status(
    request: Request,
    telegram_id: int | None = Query(default=None, description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    status = await build_access_status(session, user)
    await session.commit()
    if os.getenv("DEBUG_LIMITS") == "1":
        images = status.get("images") or {}
        logger.info(
            "access_status debug telegram_id=%s access_status=%s has_subscription=%s images=%s",
            telegram_id,
            status.get("access_status"),
            status.get("has_subscription"),
            images,
        )
    return status
