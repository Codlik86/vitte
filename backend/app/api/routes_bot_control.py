from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..users_service import get_or_create_user_by_telegram_id
from ..services.telegram_id import get_or_raise_telegram_id
from ..services.subscriptions import get_user_subscription_status
from ..bot import bot, send_pay_intro_to_user

router = APIRouter(prefix="/api/bot", tags=["bot"])


@router.post("/pay_from_miniapp")
async def pay_from_miniapp(request: Request, session: AsyncSession = Depends(get_session)):
    telegram_id = await get_or_raise_telegram_id(request)
    await get_or_create_user_by_telegram_id(session, telegram_id)
    await session.commit()
    await send_pay_intro_to_user(telegram_id)
    return {"ok": True}
