"""
Throttling middleware for rate limiting bot requests
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from shared.utils import rate_limiter, get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for rate limiting user requests

    Applies different limits for different event types
    """

    def __init__(
        self,
        message_limit: int = 10,
        message_window: int = 60,
        callback_limit: int = 20,
        callback_window: int = 60
    ):
        """
        Initialize throttling middleware

        Args:
            message_limit: Max messages per window
            message_window: Time window for messages (seconds)
            callback_limit: Max callbacks per window
            callback_window: Time window for callbacks (seconds)
        """
        super().__init__()
        self.message_limit = message_limit
        self.message_window = message_window
        self.callback_limit = callback_limit
        self.callback_window = callback_window

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process event with rate limiting

        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Handler data

        Returns:
            Handler result or None if rate limited
        """
        # Get user ID from event
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            limit = self.message_limit
            window = self.message_window
            resource = "messages"
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            limit = self.callback_limit
            window = self.callback_window
            resource = "callbacks"
        else:
            # Unknown event type - allow
            return await handler(event, data)

        if not user_id:
            # No user ID - allow (system events)
            return await handler(event, data)

        # Check rate limit
        allowed, retry_after = await rate_limiter.check_rate_limit(
            user_id=user_id,
            limit=limit,
            window=window,
            resource=resource
        )

        if not allowed:
            # Rate limit exceeded - send warning
            logger.warning(
                f"Rate limit exceeded: user_id={user_id}, "
                f"resource={resource}, retry_after={retry_after}s"
            )

            if isinstance(event, Message):
                await event.answer(
                    f"⚠️ Слишком много запросов!\n"
                    f"Подождите {retry_after} секунд перед следующим запросом.",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"⚠️ Слишком много действий! Подождите {retry_after}с",
                    show_alert=True
                )

            return None  # Stop handler chain

        # Rate limit OK - proceed
        return await handler(event, data)


class AntiFloodMiddleware(BaseMiddleware):
    """
    Simple anti-flood middleware for aggressive spam protection

    Uses stricter limits than ThrottlingMiddleware
    """

    def __init__(self, limit: int = 3, window: int = 5):
        """
        Initialize anti-flood middleware

        Args:
            limit: Max requests per window (default: 3 per 5 seconds)
            window: Time window in seconds
        """
        super().__init__()
        self.limit = limit
        self.window = window

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event with anti-flood check"""
        # Get user ID
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

        if not user_id:
            return await handler(event, data)

        # Check flood limit
        allowed, retry_after = await rate_limiter.check_rate_limit(
            user_id=user_id,
            limit=self.limit,
            window=self.window,
            resource="antiflood"
        )

        if not allowed:
            logger.warning(
                f"Anti-flood triggered: user_id={user_id}, "
                f"retry_after={retry_after}s"
            )

            if isinstance(event, Message):
                await event.answer(
                    "🚫 Обнаружен флуд! Вы заблокированы на несколько секунд.",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 Флуд обнаружен!",
                    show_alert=True
                )

            return None

        return await handler(event, data)
