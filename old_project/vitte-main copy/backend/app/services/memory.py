from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message, Dialog


async def collect_recent_memory(session: AsyncSession, dialog: Dialog, limit: int = 5) -> List[str]:
    """
    Собираем несколько последних пользовательских реплик,
    чтобы напомнить персонажу, что уже обсуждалось.
    """
    stmt = (
        select(Message)
        .where(Message.dialog_id == dialog.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    facts: List[str] = []
    for msg in messages:
        prefix = "Ты говорил" if msg.role == "user" else "Она отвечала"
        facts.append(f"{prefix}: {msg.content[:180]}".strip())
    return facts
