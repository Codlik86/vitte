"""
Chat handler - Start Chat button logic

Handles "Начать общение" button from main menu.
Checks if user has active dialog and shows appropriate options.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

from app.config import config
from shared.database import get_db
from shared.database.services import get_user_dialogs, get_user_by_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="chat")


# ==================== TEXTS ====================

# Has active dialog - offer to continue or restart
CONTINUE_DIALOG_RU = """💜 У тебя есть незавершённый разговор с {persona_name}.

Хочешь продолжить с того места или начать историю заново?"""

CONTINUE_DIALOG_EN = """💜 You have an unfinished conversation with {persona_name}.

Would you like to continue or start a new story?"""

# No active dialog - prompt to select persona
NO_DIALOG_RU = """💌 Выбери персонажа и историю, чтобы начать общение.

Открой приложение — там ждут интересные знакомства."""

NO_DIALOG_EN = """💌 Choose a character and story to start chatting.

Open the app — interesting encounters await you there."""


# ==================== KEYBOARDS ====================

def get_continue_dialog_keyboard_ru() -> InlineKeyboardMarkup:
    """Keyboard for continuing or restarting dialog (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Продолжить 💬", callback_data="chat:continue"),
            InlineKeyboardButton(text="Начать заново 🔄", callback_data="chat:restart"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="chat:back_to_menu"),
        ]
    ])


def get_continue_dialog_keyboard_en() -> InlineKeyboardMarkup:
    """Keyboard for continuing or restarting dialog (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Continue 💬", callback_data="chat:continue"),
            InlineKeyboardButton(text="Start Over 🔄", callback_data="chat:restart"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="chat:back_to_menu"),
        ]
    ])


def get_no_dialog_keyboard_ru() -> InlineKeyboardMarkup:
    """Keyboard when no active dialog (Russian)"""
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="Открыть Vitte 💜",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="Открыть Vitte 💜",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [webapp_btn],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="chat:back_to_menu")]
    ])


def get_no_dialog_keyboard_en() -> InlineKeyboardMarkup:
    """Keyboard when no active dialog (English)"""
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="Open Vitte 💜",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="Open Vitte 💜",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [webapp_btn],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="chat:back_to_menu")]
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


async def get_active_dialog_info(user_id: int) -> dict | None:
    """
    Get active dialog info for user.

    Returns:
        dict with 'id', 'persona_name' if active dialog exists
        None if no active dialog
    """
    async for db in get_db():
        dialogs = await get_user_dialogs(db, user_id, active_only=True, limit=1)
        if dialogs:
            dialog = dialogs[0]
            return {
                "id": dialog.id,
                "persona_name": dialog.title or "Персонаж",  # title as persona name for now
            }
    return None


# ==================== HANDLERS ====================

async def _show_chat_screen(user_id: int, respond_func):
    """Common logic for showing chat screen"""
    lang = await get_user_language(user_id)
    dialog_info = await get_active_dialog_info(user_id)

    if dialog_info:
        persona_name = dialog_info["persona_name"]
        if lang == "ru":
            text = CONTINUE_DIALOG_RU.format(persona_name=persona_name)
            keyboard = get_continue_dialog_keyboard_ru()
        else:
            text = CONTINUE_DIALOG_EN.format(persona_name=persona_name)
            keyboard = get_continue_dialog_keyboard_en()
        logger.info(f"User {user_id} has active dialog with {persona_name}")
    else:
        if lang == "ru":
            text = NO_DIALOG_RU
            keyboard = get_no_dialog_keyboard_ru()
        else:
            text = NO_DIALOG_EN
            keyboard = get_no_dialog_keyboard_en()
        logger.info(f"User {user_id} has no active dialog")

    await respond_func(text, reply_markup=keyboard)


@router.message(Command("chat"))
async def cmd_chat(message: Message):
    """Handle /chat command - start chat section"""
    await _show_chat_screen(message.from_user.id, message.answer)
    logger.info(f"User {message.from_user.id} opened chat via /chat command")


@router.callback_query(F.data == "menu:start_chat")
async def on_start_chat(callback: CallbackQuery):
    """Handle 'Start Chat' button from main menu"""
    await callback.answer()
    await _show_chat_screen(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data == "chat:continue")
async def on_continue_chat(callback: CallbackQuery):
    """Handle 'Continue' button - resume active dialog"""
    await callback.answer()
    user_id = callback.from_user.id

    # TODO: Actually continue the dialog with LLM
    # For now, just show placeholder
    await callback.message.answer(
        "💬 Продолжаем общение...\n\n"
        "<i>(LLM интеграция в разработке)</i>",
        parse_mode="HTML"
    )

    logger.info(f"User {user_id} chose to continue dialog")


@router.callback_query(F.data == "chat:restart")
async def on_restart_chat(callback: CallbackQuery):
    """Handle 'Start Over' button - clear memory and restart"""
    await callback.answer()
    user_id = callback.from_user.id

    # TODO: Clear dialog memory and start fresh
    # For now, just show placeholder
    await callback.message.answer(
        "🔄 Начинаем заново...\n\n"
        "<i>(Очистка памяти в разработке)</i>",
        parse_mode="HTML"
    )

    logger.info(f"User {user_id} chose to restart dialog")


@router.callback_query(F.data == "chat:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from chat")
