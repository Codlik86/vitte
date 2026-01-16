"""
Onboarding handler for new users

Flow:
1. Language selection (RU/EN)
2. Age verification (18+)
3. ... (next steps)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="onboarding")


# ==================== KEYBOARDS ====================

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Language selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ]
    ])


def get_age_verification_keyboard() -> InlineKeyboardMarkup:
    """Age verification keyboard (18+)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, мне 18+ ✓", callback_data="age:confirmed"),
        ]
    ])


# ==================== TEXTS ====================

WELCOME_TEXT = """👋 Hello!

Please select your language:"""

AGE_VERIFICATION_RU = """Привет, я Vitte 💜

Здесь только для взрослых. Если тебе 18+ — давай знакомиться.

<i>(контент на утверждении)</i>"""

AGE_VERIFICATION_EN = """Hi, I'm Vitte 💜

This is for adults only. If you're 18+ — let's get to know each other.

<i>(content pending approval)</i>"""

ENGLISH_WIP = """🚧 English version is under development.

Please select Russian for now."""


# ==================== HANDLERS ====================

@router.callback_query(F.data == "lang:ru")
async def on_language_russian(callback: CallbackQuery):
    """Handle Russian language selection"""
    await callback.answer()

    # Edit message to show age verification
    await callback.message.edit_text(
        AGE_VERIFICATION_RU,
        reply_markup=get_age_verification_keyboard(),
        parse_mode="HTML"
    )

    logger.info(f"User {callback.from_user.id} selected Russian")


@router.callback_query(F.data == "lang:en")
async def on_language_english(callback: CallbackQuery):
    """Handle English language selection - WIP"""
    await callback.answer(ENGLISH_WIP, show_alert=True)

    logger.info(f"User {callback.from_user.id} tried English (WIP)")


@router.callback_query(F.data == "age:confirmed")
async def on_age_confirmed(callback: CallbackQuery):
    """Handle age confirmation (18+) -> show main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    # Show main menu (Russian for now)
    await show_main_menu(callback, lang="ru", edit=True)

    logger.info(f"User {callback.from_user.id} confirmed 18+ -> main menu")
