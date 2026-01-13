"""
Internationalization (i18n) manager for Vitte bot

This module provides translation capabilities using aiogram-i18n.
Supports JSON-based translations with database persistence.
"""
from pathlib import Path
from typing import Any, Dict

from aiogram import Bot
from aiogram.types import User
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore


# Get locales directory path
LOCALES_DIR = Path(__file__).parent


class DatabaseUserLocale:
    """
    Custom locale getter that fetches user's language preference from database.

    Falls back to Telegram's language_code if not set in DB.
    """

    def __init__(self):
        self.cache: Dict[int, str] = {}

    async def get_locale(self, event_from_user: User, **kwargs) -> str:
        """
        Get user's preferred locale.

        Priority:
        1. Database language_code (future implementation)
        2. Telegram user language_code
        3. Default: "ru"

        Args:
            event_from_user: Telegram user object

        Returns:
            Language code (e.g., "ru", "en")
        """
        user_id = event_from_user.id

        # Check cache first
        if user_id in self.cache:
            return self.cache[user_id]

        # TODO: Fetch from database when User model has language_code field
        # from shared.database import get_user_by_id
        # async with get_db() as db:
        #     user = await get_user_by_id(db, user_id)
        #     if user and user.language_code:
        #         self.cache[user_id] = user.language_code
        #         return user.language_code

        # Fallback to Telegram language or default
        locale = event_from_user.language_code or "ru"

        # Normalize locale (support "ru-RU" -> "ru", "en-US" -> "en")
        locale = locale.split("-")[0].lower()

        # Only support ru/en for now
        if locale not in ["ru", "en"]:
            locale = "ru"

        self.cache[user_id] = locale
        return locale

    def invalidate(self, user_id: int):
        """Invalidate cache when user changes language"""
        self.cache.pop(user_id, None)


# Initialize locale getter
locale_getter = DatabaseUserLocale()


# Initialize i18n core with Fluent
# Note: We use FluentRuntimeCore for better syntax, but JSON files work too
i18n_core = FluentRuntimeCore(
    path=LOCALES_DIR,
    raise_key_error=False,  # Don't crash on missing translations
    locales_map={
        "ru": ("ru", "en"),  # Russian with English fallback
        "en": ("en", "ru"),  # English with Russian fallback
    }
)


# Create i18n middleware
i18n_middleware = I18nMiddleware(
    core=i18n_core,
    manager=locale_getter,
    default_locale="ru",
)


def setup_i18n(bot: Bot):
    """
    Setup i18n for the bot.

    This function is called during bot initialization to register
    the i18n middleware.

    Args:
        bot: Bot instance
    """
    # Middleware is registered in bot.py
    pass
