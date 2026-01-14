from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PersonaEvent, PersonaEventType


async def log_persona_event(
    session: AsyncSession,
    *,
    user_id: int,
    persona_id: int | None,
    event_type: PersonaEventType,
) -> None:
    event = PersonaEvent(
        user_id=user_id,
        persona_id=persona_id,
        event_type=event_type,
    )
    session.add(event)
