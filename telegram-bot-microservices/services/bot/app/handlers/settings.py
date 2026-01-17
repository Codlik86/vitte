"""
Settings handler - Main settings screen

Handles settings button from main menu.
Shows language selection and clear history options.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from shared.database import get_db
from shared.database.services import get_user_by_id, update_user
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="settings")


# ==================== TEXTS ====================

SETTINGS_RU = """⚙️ <b>Основные настройки</b>

Здесь ты можешь настроить Vitte под себя."""

SETTINGS_EN = """⚙️ <b>Settings</b>

Customize your Vitte experience."""

LANGUAGE_SELECT_RU = """🌐 <b>Выбор языка</b>

Выбери язык интерфейса:"""

LANGUAGE_SELECT_EN = """🌐 <b>Language Selection</b>

Choose your interface language:"""


# ==================== KEYBOARDS ====================

def get_settings_keyboard(lang: str, current_lang: str) -> InlineKeyboardMarkup:
    """Settings keyboard with dynamic language button"""
    # Language button shows current language with flag
    if current_lang == "ru":
        lang_btn_text = "🇷🇺 Язык: Русский" if lang == "ru" else "🇷🇺 Language: Russian"
    else:
        lang_btn_text = "🇬🇧 Язык: English" if lang == "ru" else "🇬🇧 Language: English"

    # Clear history button (disabled for now)
    clear_text = "🗑 Очистить историю" if lang == "ru" else "🗑 Clear history"
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=lang_btn_text, callback_data="settings:language"),
        ],
        [
            InlineKeyboardButton(text=clear_text, callback_data="settings:clear_history"),
        ],
        [
            InlineKeyboardButton(text=back_text, callback_data="settings:back_to_menu"),
        ]
    ])


def get_language_select_keyboard(lang: str, current_lang: str) -> InlineKeyboardMarkup:
    """Language selection keyboard"""
    # Russian button - active or not
    ru_text = "🇷🇺 Русский"
    if current_lang == "ru":
        ru_text += " ✓"

    # English button - in development
    en_text = "🇬🇧 English"
    if current_lang == "en":
        en_text += " ✓"
    else:
        en_text += " (soon)" if lang == "en" else " (скоро)"

    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=ru_text, callback_data="settings:lang_ru"),
        ],
        [
            InlineKeyboardButton(text=en_text, callback_data="settings:lang_en"),
        ],
        [
            InlineKeyboardButton(text=back_text, callback_data="settings:back_to_settings"),
        ]
    ])


# ==================== HELPER FUNCTIONS ====================

async def get_user_language(user_id: int) -> str:
    """Get user language from DB, default to 'ru'"""
    async for db in get_db():
        user = await get_user_by_id(db, user_id)
        if user:
            # Handle both dict (from cache) and SQLAlchemy object
            if isinstance(user, dict):
                return user.get("language_code", "ru")
            else:
                return user.language_code or "ru"
    return "ru"


# ==================== HANDLERS ====================

@router.callback_query(F.data == "menu:settings")
async def on_settings(callback: CallbackQuery):
    """Handle 'Settings' button from main menu"""
    await callback.answer()
    user_id = callback.from_user.id

    # Get user language
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = SETTINGS_RU
    else:
        text = SETTINGS_EN

    keyboard = get_settings_keyboard(lang=lang, current_lang=lang)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User {user_id} opened settings")


@router.callback_query(F.data == "settings:language")
async def on_language_select(callback: CallbackQuery):
    """Handle 'Language' button - show language selection"""
    await callback.answer()
    user_id = callback.from_user.id

    # Get user language
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = LANGUAGE_SELECT_RU
    else:
        text = LANGUAGE_SELECT_EN

    keyboard = get_language_select_keyboard(lang=lang, current_lang=lang)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User {user_id} opened language selection")


@router.callback_query(F.data == "settings:lang_ru")
async def on_select_russian(callback: CallbackQuery):
    """Handle Russian language selection"""
    user_id = callback.from_user.id
    current_lang = await get_user_language(user_id)

    if current_lang == "ru":
        await callback.answer("🇷🇺 Русский уже выбран", show_alert=False)
    else:
        # Update language in DB
        async for db in get_db():
            await update_user(db, user_id, language_code="ru")
        await callback.answer("🇷🇺 Язык изменён на Русский", show_alert=True)

        # Refresh language selection screen
        text = LANGUAGE_SELECT_RU
        keyboard = get_language_select_keyboard(lang="ru", current_lang="ru")
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User {user_id} selected Russian language")


@router.callback_query(F.data == "settings:lang_en")
async def on_select_english(callback: CallbackQuery):
    """Handle English language selection - in development"""
    lang = await get_user_language(callback.from_user.id)

    if lang == "ru":
        await callback.answer("🚧 Английский язык в разработке", show_alert=True)
    else:
        await callback.answer("🚧 English is coming soon", show_alert=True)

    logger.info(f"User {callback.from_user.id} tried to select English (in development)")


@router.callback_query(F.data == "settings:clear_history")
async def on_clear_history(callback: CallbackQuery):
    """Handle 'Clear history' button - in development"""
    lang = await get_user_language(callback.from_user.id)

    if lang == "ru":
        await callback.answer("🚧 Очистка истории в разработке", show_alert=True)
    else:
        await callback.answer("🚧 Clear history coming soon", show_alert=True)

    logger.info(f"User {callback.from_user.id} tried to clear history (in development)")


@router.callback_query(F.data == "settings:back_to_settings")
async def on_back_to_settings(callback: CallbackQuery):
    """Handle 'Back' button from language selection - return to settings"""
    await callback.answer()
    user_id = callback.from_user.id

    # Get user language
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = SETTINGS_RU
    else:
        text = SETTINGS_EN

    keyboard = get_settings_keyboard(lang=lang, current_lang=lang)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User {user_id} returned to settings from language selection")


@router.callback_query(F.data == "settings:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from settings")
