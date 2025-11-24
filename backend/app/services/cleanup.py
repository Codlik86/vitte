from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import async_session_factory
from ..logging_config import logger
from .qdrant_service import enforce_qdrant_limits

# Data retention windows
MESSAGES_TTL_DAYS = 60
EVENTS_TTL_DAYS = 90
VECTORS_PER_USER_LIMIT = 300  # placeholder for future Qdrant cleanup


async def start_cleanup_worker() -> asyncio.Task:
    return asyncio.create_task(_cleanup_loop(), name="cleanup-loop")


async def _cleanup_loop():
    while True:
        try:
            async with async_session_factory() as session:
                await run_cleanup(session)
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("Cleanup loop error: %s", exc)
        await asyncio.sleep(6 * 60 * 60)  # every 6 hours


def cleanup_status() -> str:
    for task in asyncio.all_tasks():
        if task.get_name() == "cleanup-loop":
            return "running" if not task.cancelled() else "stopped"
    return "stopped"


async def run_cleanup(session: AsyncSession):
    await _cleanup_messages(session)
    await _cleanup_events(session)
    try:
        enforce_qdrant_limits()
    except Exception as exc:  # noqa: BLE001
        logger.error("Qdrant cleanup failed: %s", exc)


async def _cleanup_messages(session: AsyncSession):
    cutoff = datetime.utcnow() - timedelta(days=MESSAGES_TTL_DAYS)
    # Keep the most recent 50 messages per dialog to preserve context
    stmt = text(
        """
        WITH ranked AS (
            SELECT id, dialog_id, created_at,
                   ROW_NUMBER() OVER (PARTITION BY dialog_id ORDER BY created_at DESC) AS rn
            FROM messages
            WHERE created_at < :cutoff
        )
        DELETE FROM messages
        WHERE id IN (
            SELECT id FROM ranked WHERE rn > 50
        );
        """
    )
    result = await session.execute(stmt, {"cutoff": cutoff})
    deleted = result.rowcount or 0
    if deleted:
        logger.info("Cleanup: deleted %s old messages (cutoff %s)", deleted, cutoff.isoformat())


async def _cleanup_events(session: AsyncSession):
    cutoff = datetime.utcnow() - timedelta(days=EVENTS_TTL_DAYS)
    result = await session.execute(
        text("DELETE FROM events_analytics WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    deleted = result.rowcount or 0
    if deleted:
        logger.info("Cleanup: deleted %s old analytics events (cutoff %s)", deleted, cutoff.isoformat())
