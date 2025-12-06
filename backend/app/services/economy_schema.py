from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_economy_schema(session: AsyncSession) -> None:
    """No-op: schema managed by migrations; runtime DDL removed."""
    return None
