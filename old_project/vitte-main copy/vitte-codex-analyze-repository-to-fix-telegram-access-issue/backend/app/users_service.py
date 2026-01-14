from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User


async def get_or_create_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.flush()
    return user
