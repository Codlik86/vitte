from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..users_service import get_or_create_user_by_telegram_id
from ..services.access import build_access_status
from ..schemas import AccessStatusResponse

router = APIRouter(prefix="/api/access", tags=["access"])


@router.get("/status", response_model=AccessStatusResponse)
async def access_status(
    telegram_id: int = Query(..., description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    status = await build_access_status(session, user)
    await session.commit()
    return status
