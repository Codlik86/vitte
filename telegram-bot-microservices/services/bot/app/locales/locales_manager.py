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
from aiogram_i18n.managers import BaseManager


# Get locales directory path
LOCALES_DIR = Path(__file__).parent


# Locale cache for performance
_locale_cache: Dict[int, str] = {}


async def get_user_locale(event_from_user: User, **kwargs) -> str:
    """
    Get user's preferred locale.

    Priority:
    1. Cache
    2. Telegram user language_code
    3. Default: "ru"

    Args:
        event_from_user: Telegram user object

    Returns:
        Language code (e.g., "ru", "en")
    """
    user_id = event_from_user.id

    # Check cache first
    if user_id in _locale_cache:
        return _locale_cache[user_id]

    # TODO: Fetch from database when User model has language_code field
    # from shared.database import get_user_by_id, get_db
    # async for db in get_db():
    #     user = await get_user_by_id(db, user_id)
    #     if user and user.language_code:
    #         _locale_cache[user_id] = user.language_code
    #         return user.language_code
    #     break

    # Fallback to Telegram language or default
    locale = event_from_user.language_code or "ru"

    # Normalize locale (support "ru-RU" -> "ru", "en-US" -> "en")
    locale = locale.split("-")[0].lower()

    # Only support ru/en for now
    if locale not in ["ru", "en"]:
        locale = "ru"

    _locale_cache[user_id] = locale
    return locale


def invalidate_locale_cache(user_id: int):
    """Invalidate cache when user changes language"""
    _locale_cache.pop(user_id, None)


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


# Custom locale manager for i18n middleware
class CustomLocaleManager(BaseManager):
    """
    Custom locale manager with caching support.

    This manager determines user's language from:
    1. Cache (for performance)
    2. Telegram user's language_code
    3. Fallback to default "ru"
    """

    async def get_locale(self, *, event, **kwargs) -> str:
        """
        Get user's locale from event.

        Args:
            event: Telegram event (Message, CallbackQuery, etc.)
            **kwargs: Additional middleware data

        Returns:
            Language code (e.g., "ru", "en")
        """
        if hasattr(event, 'from_user') and event.from_user:
            return await get_user_locale(event.from_user)
        # Fallback to default
        return "ru"

    async def set_locale(self, *, locale: str, event, **kwargs) -> None:
        """
        Set user's locale (optional - for future language selection feature).

        Args:
            locale: Language code to set
            event: Telegram event
            **kwargs: Additional middleware data
        """
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            _locale_cache[user_id] = locale
            # TODO: Save to database when language selection is implemented


# Create i18n middleware with custom locale manager
i18n_middleware = I18nMiddleware(
    core=i18n_core,
    manager=CustomLocaleManager(default_locale="ru"),
    default_locale="ru"
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
