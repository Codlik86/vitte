"""
Settings handler - Main settings screen

Handles settings button from main menu.
Shows language selection and clear history options.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from shared.database import get_db
from shared.database.services import get_user_by_id, update_user
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="settings")


# ==================== TEXTS ====================

SETTINGS_RU = """⚙️ <b>Основные настройки</b>

Здесь ты можешь настроить CraveMe под себя."""

SETTINGS_EN = """⚙️ <b>Settings</b>

Customize your CraveMe experience."""

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

    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=lang_btn_text, callback_data="settings:language"),
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

    # Spanish button - coming soon
    es_text = "🇪🇸 Español"
    if current_lang == "es":
        es_text += " ✓"
    else:
        es_text += " (soon)" if lang == "en" else " (скоро)"

    # German button - coming soon
    de_text = "🇩🇪 Deutsch"
    if current_lang == "de":
        de_text += " ✓"
    else:
        de_text += " (soon)" if lang == "en" else " (скоро)"

    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=ru_text, callback_data="settings:lang_ru"),
        ],
        [
            InlineKeyboardButton(text=en_text, callback_data="settings:lang_en"),
        ],
        [
            InlineKeyboardButton(text=es_text, callback_data="settings:lang_es"),
        ],
        [
            InlineKeyboardButton(text=de_text, callback_data="settings:lang_de"),
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

async def _show_settings_screen(user_id: int, respond_func):
    """Common logic for showing settings screen"""
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = SETTINGS_RU
    else:
        text = SETTINGS_EN

    keyboard = get_settings_keyboard(lang=lang, current_lang=lang)
    await respond_func(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} opened settings")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command"""
    await _show_settings_screen(message.from_user.id, message.answer)


@router.callback_query(F.data == "menu:settings")
async def on_settings(callback: CallbackQuery):
    """Handle 'Settings' button from main menu"""
    await callback.answer()
    await _show_settings_screen(callback.from_user.id, callback.message.answer)


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


@router.callback_query(F.data == "settings:lang_es")
async def on_select_spanish(callback: CallbackQuery):
    """Handle Spanish language selection - in development"""
    lang = await get_user_language(callback.from_user.id)

    if lang == "ru":
        await callback.answer("🚧 Испанский язык в разработке", show_alert=True)
    else:
        await callback.answer("🚧 Spanish is in development", show_alert=True)

    logger.info(f"User {callback.from_user.id} tried to select Spanish (in development)")


@router.callback_query(F.data == "settings:lang_de")
async def on_select_german(callback: CallbackQuery):
    """Handle German language selection - in development"""
    lang = await get_user_language(callback.from_user.id)

    if lang == "ru":
        await callback.answer("🚧 Немецкий язык в разработке", show_alert=True)
    else:
        await callback.answer("🚧 German is in development", show_alert=True)

    logger.info(f"User {callback.from_user.id} tried to select German (in development)")




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
