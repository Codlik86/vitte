from __future__ import annotations

from typing import Any, Awaitable, Callable
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from ..logging_config import logger
from ..db import get_session, AsyncSession
from ..models import User
from ..services.onboarding import onboarding_text, build_terms_keyboard
from ..users_service import get_or_create_user_by_telegram_id


class TermsGateMiddleware(BaseMiddleware):
    """
    Блокирует любые действия, пока пользователь не подтвердил 18+ и правила.
    Разрешены только /start, /help и колбэки онбординга.
    """

    allowed_callbacks = {"onb_accept_terms", "onb_reject_terms"}
    allowed_commands = {"/start", "start", "/help", "help"}

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        message: Message | None = getattr(event, "message", None)
        callback: CallbackQuery | None = getattr(event, "callback_query", None)

        # Для callback-запросов берём пользователя из callback.from_user,
        # а message используем только как контейнер для текста/ответа.
        actor = callback.from_user if callback else (message.from_user if message else None)
        if callback and callback.message:
            message = callback.message

        if message is None or actor is None:
            return await handler(event, data)

        text = (message.text or "").strip() if message.text else ""
        is_allowed_command = text.lower() in self.allowed_commands
        is_allowed_callback = callback and callback.data in self.allowed_callbacks

        telegram_id = actor.id

        async for session in get_session():  # type: AsyncSession
            user = await get_or_create_user_by_telegram_id(session, telegram_id)
            data.setdefault("db_session", session)
            data.setdefault("current_user", user)

            if user.accepted_terms_at and user.is_adult_confirmed:
                return await handler(event, data)

            if is_allowed_command or is_allowed_callback:
                await session.commit()
                return await handler(event, data)

            try:
                if message:
                    await message.answer(onboarding_text(), reply_markup=build_terms_keyboard())
                elif callback:
                    await callback.answer(onboarding_text(), show_alert=True)
            except Exception as exc:
                logger.error("Failed to send onboarding reminder: %s", exc)
            await session.commit()
            return
