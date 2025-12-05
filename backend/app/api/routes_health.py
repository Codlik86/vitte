from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session, async_session_factory
from ..logging_config import logger
from ..services.retention import retention_status
from ..services.cleanup import cleanup_status
from ..services.qdrant_service import get_qdrant_client, QDRANT_COLLECTIONS
from ..config import settings

router = APIRouter(tags=["system"])


@router.get("/health", summary="Healthcheck")
async def health():
    return {"status": "ok"}


@router.get("/health/extended", summary="Extended healthcheck")
async def health_extended(session: AsyncSession = Depends(get_session)):
    statuses = {
        "postgres": "unknown",
        "qdrant": "not_configured",
        "llm": "skipped",
        "retention_worker": "unknown",
        "cleanup_worker": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        await session.execute(text("SELECT 1"))
        statuses["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.error("Healthcheck postgres failed: %s", exc)
        statuses["postgres"] = "error"

    if settings.qdrant_url:
        try:
            client = get_qdrant_client()
            if client:
                client.get_collections()
                statuses["qdrant"] = "ok"
            else:
                statuses["qdrant"] = "not_configured"
        except Exception as exc:  # noqa: BLE001
            logger.error("Healthcheck qdrant failed: %s", exc)
            statuses["qdrant"] = "error"

    if settings.proxyapi_api_key or settings.openai_api_key:
        statuses["llm"] = "skipped"  # avoid external call in health

    retention = retention_status()
    statuses["retention_worker"] = retention

    statuses["cleanup_worker"] = cleanup_status()

    overall = "ok" if all(v in ("ok", "running", "skipped", "not_configured") for v in statuses.values()) else "degraded"
    statuses["status"] = overall
    return statuses
