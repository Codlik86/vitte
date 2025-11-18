from fastapi import APIRouter, Request, Header, HTTPException

from ..config import settings
from ..bot import handle_update

router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    update = await request.json()
    await handle_update(update)
    return {"ok": True}
