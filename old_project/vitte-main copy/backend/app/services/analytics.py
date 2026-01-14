from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EventAnalytics


async def log_event(
    session: AsyncSession,
    user_id: int | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> EventAnalytics:
    """
    Lightweight helper used across the backend to persist monetization events.
    """
    event = EventAnalytics(
        user_id=user_id,
        event_type=event_type,
        payload=payload or {},
    )
    session.add(event)
    return event
