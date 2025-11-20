from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from ..config import settings
from ..db import get_session, AsyncSession
from ..models import User, AccessStatus, EventAnalytics
from ..logging_config import logger
from ..services.access import get_active_subscription


class AccessMiddleware(BaseMiddleware):
    """
    Middleware уровня update: следит за лимитом бесплатных сообщений
    и статусом подписки.
    """

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        # Нас интересуют только апдейты с message или callback_query
        message: Message | None = getattr(event, "message", None)
        if message is None:
            callback: CallbackQuery | None = getattr(event, "callback_query", None)
            if callback:
                message = callback.message

        if message is None or message.from_user is None:
            return await handler(event, data)

        telegram_id = message.from_user.id

        # Не блокируем команды /health и подобные системные вещи (на будущее)
        text = (message.text or "").strip() if message.text else ""
        if text.startswith("/health"):
            return await handler(event, data)

        # Подключаем сессию БД через зависимость get_session
        async for session in get_session():  # type: AsyncSession
            user = await self._get_or_create_user(session, telegram_id)
            data["db_session"] = session
            data["current_user"] = user

            subscription = await get_active_subscription(session, user.id)

            # Если подписка активна — ничего не ограничиваем
            if subscription or user.access_status == AccessStatus.SUBSCRIPTION_ACTIVE:
                if subscription and user.access_status != AccessStatus.SUBSCRIPTION_ACTIVE:
                    user.access_status = AccessStatus.SUBSCRIPTION_ACTIVE
                await self._log_event(session, user, "message_allowed", {"reason": "subscription_active"})
                await session.commit()
                return await handler(event, data)

            # Считаем бесплатные сообщения только для обычного текста
            # и только если это не команда /pay
            if text.startswith("/pay"):
                await self._log_event(session, user, "pay_command_called", {})
                await session.commit()
                return await handler(event, data)

            # Проверяем лимит
            if user.free_messages_used >= settings.free_messages_limit:
                # Лимит исчерпан — отправляем пейвол
                await self._log_event(session, user, "message_blocked_paywall", {
                    "limit": settings.free_messages_limit,
                })
                await session.commit()

                try:
                    await message.answer(
                        f"Похоже, ты уже использовал свои {settings.free_messages_limit} бесплатных сообщений 💌\n\n"
                        "Чтобы продолжить общение и открыть больше возможностей, "
                        "оформи подписку. Напиши /pay или открой мини-приложение Vitte."
                    )
                except Exception as e:
                    logger.error(f"Failed to send paywall message: {e}")

                # Не пропускаем дальше
                return

            # Лимит не достигнут — позволяем сообщение и увеличиваем счётчик
            user.free_messages_used += 1
            await self._log_event(session, user, "message_allowed", {
                "used": user.free_messages_used,
                "limit": settings.free_messages_limit,
            })
            await session.commit()

            return await handler(event, data)

    @staticmethod
    async def _get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.flush()
        return user

    @staticmethod
    async def _log_event(session: AsyncSession, user: User, event_type: str, payload: dict | None = None):
        event = EventAnalytics(
            user_id=user.id,
            event_type=event_type,
            payload=payload or {},
        )
        session.add(event)
