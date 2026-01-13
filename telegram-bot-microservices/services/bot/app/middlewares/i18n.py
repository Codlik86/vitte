"""
i18n middleware exports

This module re-exports i18n middleware from locales_manager for cleaner imports.
"""
from app.locales.locales_manager import i18n_middleware, get_user_locale, invalidate_locale_cache

__all__ = ["i18n_middleware", "get_user_locale", "invalidate_locale_cache"]
