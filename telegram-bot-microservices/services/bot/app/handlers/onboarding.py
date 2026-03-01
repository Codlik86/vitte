"""
Onboarding handler for new users

Flow:
1. Language selection (RU/EN)
2. Age verification (18+)
3. ... (next steps)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommandScopeChat

from shared.database import get_db
from shared.database.services import update_user
from shared.utils import get_logger
from app.commands import COMMANDS_RU, COMMANDS_EN

logger = get_logger(__name__)
router = Router(name="onboarding")


# ==================== KEYBOARDS ====================

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Language selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang:es"),
            InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang:de"),
        ]
    ])


def get_age_verification_keyboard() -> InlineKeyboardMarkup:
    """Age verification keyboard (18+)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, мне 18+ ", callback_data="age:confirmed"),
        ]
    ])


# ==================== TEXTS ====================

WELCOME_TEXT = """💜 Hello!

Please select your language:"""

AGE_VERIFICATION_RU = """Привет, я CraveMe 💜

Здесь только для взрослых. Если тебе 18+ — давай знакомиться.

<i>(контент на утверждении)</i>"""

AGE_VERIFICATION_EN = """Hi, I'm CraveMe 💜

This is for adults only. If you're 18+ — let's get to know each other.

<i>(content pending approval)</i>"""

ENGLISH_WIP = """🚧 English version is under development.

Please select Russian for now."""

SPANISH_WIP = """🚧 La versión en español está en desarrollo.

Por favor selecciona Ruso por ahora."""

GERMAN_WIP = """🚧 Die deutsche Version befindet sich in der Entwicklung.

Bitte wähle vorerst Russisch."""


# ==================== HANDLERS ====================

@router.callback_query(F.data == "lang:ru")
async def on_language_russian(callback: CallbackQuery):
    """Handle Russian language selection"""
    await callback.answer()
    user_id = callback.from_user.id

    # Save language to DB
    async for db in get_db():
        await update_user(db, user_id, language_code="ru")

    # Set Russian commands for this user
    await callback.bot.set_my_commands(
        commands=COMMANDS_RU,
        scope=BotCommandScopeChat(chat_id=user_id)
    )

    # Edit message to show age verification
    await callback.message.edit_text(
        AGE_VERIFICATION_RU,
        reply_markup=get_age_verification_keyboard(),
        parse_mode="HTML"
    )

    logger.info(f"User {user_id} selected Russian, commands set")


@router.callback_query(F.data == "lang:en")
async def on_language_english(callback: CallbackQuery):
    """Handle English language selection"""
    await callback.answer()
    user_id = callback.from_user.id

    # Save language to DB
    async for db in get_db():
        await update_user(db, user_id, language_code="en")

    # Invalidate locale cache so i18n picks up new language
    from app.locales.locales_manager import invalidate_locale_cache
    invalidate_locale_cache(user_id)

    # Set English commands for this user
    await callback.bot.set_my_commands(
        commands=COMMANDS_EN,
        scope=BotCommandScopeChat(chat_id=user_id)
    )

    # Show age verification in English
    await callback.message.edit_text(
        AGE_VERIFICATION_EN,
        reply_markup=get_age_verification_keyboard(),
        parse_mode="HTML"
    )

    logger.info(f"User {user_id} selected English, commands set")


@router.callback_query(F.data == "lang:es")
async def on_language_spanish(callback: CallbackQuery):
    """Handle Spanish language selection - WIP"""
    await callback.answer(SPANISH_WIP, show_alert=True)
    logger.info(f"User {callback.from_user.id} tried Spanish (in development)")


@router.callback_query(F.data == "lang:de")
async def on_language_german(callback: CallbackQuery):
    """Handle German language selection - WIP"""
    await callback.answer(GERMAN_WIP, show_alert=True)
    logger.info(f"User {callback.from_user.id} tried German (in development)")


@router.callback_query(F.data == "age:confirmed")
async def on_age_confirmed(callback: CallbackQuery):
    """Handle age confirmation (18+) -> show welcome menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    # Get user's selected language from DB
    user_id = callback.from_user.id
    async for db in get_db():
        from shared.database.services import get_user_by_id as _get_user
        user = await _get_user(db, user_id)
        lang = "ru"
        if user:
            lang_code = user.get("language_code") if isinstance(user, dict) else user.language_code
            if lang_code in ["ru", "en"]:
                lang = lang_code
        break

    # Show welcome menu for first-time users
    await show_main_menu(callback, lang=lang, is_welcome=True)

    logger.info(f"User {user_id} confirmed 18+ -> welcome menu (lang={lang})")
