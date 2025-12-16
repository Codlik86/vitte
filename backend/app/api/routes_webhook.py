import asyncio
import time

from fastapi import APIRouter, Request, Header, HTTPException
from sqlalchemy import text

from ..db import async_session_factory
from ..config import settings
from ..bot import handle_update
from ..logging_config import logger

router = APIRouter(tags=["telegram"])

WEBHOOK_PATH = f"/webhook/{settings.telegram_webhook_secret or 'telegram'}"


async def _log_stage(update_id: int | None, start_time: float, stage: str) -> None:
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info("update_id=%s stage=%s elapsed_ms=%s", update_id, stage, elapsed_ms)


async def process_update_safe(update: dict, start_time: float, update_id: int | None) -> None:
    try:
        await _log_stage(update_id, start_time, "llm")
        await handle_update(update)
        await _log_stage(update_id, start_time, "send")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to process update %s", update_id)


async def cleanup_processed_updates(ttl_days: int = 14) -> None:
    async with async_session_factory() as session:
        await session.execute(
            text(
                """
                DELETE FROM processed_updates
                WHERE created_at < now() - (:ttl_days || ' days')::interval
                """
            ),
            {"ttl_days": ttl_days},
        )
        await session.commit()


@router.post(WEBHOOK_PATH)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    start_time = time.perf_counter()
    update = await request.json()
    update_id = update.get("update_id")
    await _log_stage(update_id, start_time, "received")

    if update_id is not None:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO processed_updates (update_id)
                    VALUES (:update_id)
                    ON CONFLICT DO NOTHING
                    RETURNING 1
                    """
                ),
                {"update_id": update_id},
            )
            inserted = result.scalar() is not None
            await session.commit()
        await _log_stage(update_id, start_time, "db")
        if not inserted:
            return {"ok": True}

    asyncio.create_task(process_update_safe(update, start_time, update_id))
    return {"ok": True}
