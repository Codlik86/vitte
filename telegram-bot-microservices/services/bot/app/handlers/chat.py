"""
Chat handler - Start Chat button logic

Handles "Начать общение" button from main menu.
Shows active dialogs list or prompts to create new.
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import config
from shared.database import get_db, Dialog, Persona
from shared.database.services import get_user_dialogs, get_user_by_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="chat")


# ==================== TEXTS ====================

# Has active dialogs
HAS_DIALOGS_RU = """💜 Твои активные диалоги

Выбери с кем продолжить общение или начни новый диалог."""

HAS_DIALOGS_EN = """💜 Your active dialogs

Choose who to continue chatting with or start a new dialog."""

# No active dialogs
NO_DIALOGS_RU = """💌 У тебя пока нет активных диалогов.

Открой приложение — выбери персонажа и начни общение."""

NO_DIALOGS_EN = """💌 You don't have any active dialogs yet.

Open the app — choose a character and start chatting."""


# ==================== KEYBOARDS ====================

def format_dialog_date(dt: datetime | None) -> str:
    """Format dialog date for display"""
    if not dt:
        return ""
    now = datetime.utcnow()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    return dt.strftime("%d.%m")


def get_dialogs_keyboard_ru(dialogs: list[Dialog], can_create_new: bool = True) -> InlineKeyboardMarkup:
    """Build keyboard with active dialogs (Russian)"""
    buttons = []

    # New dialog button (if less than 3 active)
    if can_create_new:
        if config.webapp_url:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ Новый диалог",
                    web_app=WebAppInfo(url=config.webapp_url)
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ Новый диалог",
                    callback_data="menu:open_webapp"
                )
            ])

    # Dialog buttons
    for dialog in dialogs:
        persona_name = "Персонаж"
        if dialog.persona:
            persona_name = dialog.persona.name

        date_str = format_dialog_date(dialog.updated_at or dialog.created_at)
        label = f"💬 {persona_name}"
        if date_str:
            label += f" • {date_str}"

        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"chat:continue:{dialog.id}"
            )
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="chat:back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dialogs_keyboard_en(dialogs: list[Dialog], can_create_new: bool = True) -> InlineKeyboardMarkup:
    """Build keyboard with active dialogs (English)"""
    buttons = []

    # New dialog button (if less than 3 active)
    if can_create_new:
        if config.webapp_url:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ New dialog",
                    web_app=WebAppInfo(url=config.webapp_url)
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ New dialog",
                    callback_data="menu:open_webapp"
                )
            ])

    # Dialog buttons
    for dialog in dialogs:
        persona_name = "Character"
        if dialog.persona:
            persona_name = dialog.persona.name

        date_str = format_dialog_date(dialog.updated_at or dialog.created_at)
        label = f"💬 {persona_name}"
        if date_str:
            label += f" • {date_str}"

        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"chat:continue:{dialog.id}"
            )
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="chat:back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_no_dialogs_keyboard_ru() -> InlineKeyboardMarkup:
    """Keyboard when no active dialogs (Russian)"""
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


def get_no_dialogs_keyboard_en() -> InlineKeyboardMarkup:
    """Keyboard when no active dialogs (English)"""
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
            if isinstance(user, dict):
                return user.get("language_code", "ru")
            else:
                return user.language_code or "ru"
    return "ru"


async def get_active_dialogs_with_personas(user_id: int) -> list[Dialog]:
    """Get active dialogs with persona info loaded"""
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.user_id == user_id, Dialog.is_active == True)
            .order_by(Dialog.updated_at.desc())
            .limit(3)
        )
        return list(result.scalars().all())
    return []


# ==================== HANDLERS ====================

async def _show_chat_screen(user_id: int, respond_func):
    """Common logic for showing chat screen"""
    lang = await get_user_language(user_id)
    dialogs = await get_active_dialogs_with_personas(user_id)

    if dialogs:
        can_create_new = len(dialogs) < 3
        if lang == "ru":
            text = HAS_DIALOGS_RU
            keyboard = get_dialogs_keyboard_ru(dialogs, can_create_new)
        else:
            text = HAS_DIALOGS_EN
            keyboard = get_dialogs_keyboard_en(dialogs, can_create_new)
        logger.info(f"User {user_id} has {len(dialogs)} active dialog(s)")
    else:
        if lang == "ru":
            text = NO_DIALOGS_RU
            keyboard = get_no_dialogs_keyboard_ru()
        else:
            text = NO_DIALOGS_EN
            keyboard = get_no_dialogs_keyboard_en()
        logger.info(f"User {user_id} has no active dialogs")

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


@router.callback_query(F.data.startswith("chat:continue:"))
async def on_continue_dialog(callback: CallbackQuery):
    """Handle 'Continue' button - resume specific dialog"""
    await callback.answer()
    user_id = callback.from_user.id

    # Extract dialog_id from callback data
    dialog_id = int(callback.data.split(":")[-1])

    # Get dialog with persona
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.id == dialog_id, Dialog.user_id == user_id)
        )
        dialog = result.scalar_one_or_none()

        if not dialog:
            await callback.message.answer("❌ Диалог не найден")
            return

        persona_name = dialog.persona.name if dialog.persona else "Персонаж"
        persona_id = dialog.persona_id

        # Show "generating" message
        await callback.message.answer(
            f"💬 Продолжаем общение с <b>{persona_name}</b>...",
            parse_mode="HTML"
        )

        # Generate return greeting via API (will be sent to Telegram by API)
        from app.services.api_client import generate_greeting
        result = await generate_greeting(
            telegram_id=user_id,
            persona_id=persona_id,
            story_id=dialog.story_id,
            atmosphere=dialog.atmosphere,
            is_return=True,
            send_to_telegram=True,  # API will send greeting to Telegram
        )

        if not result.success:
            logger.warning(f"Failed to generate greeting for user {user_id}: {result.error}")
            # Fallback - just tell user to write
            await callback.message.answer(
                "Напиши сообщение, чтобы продолжить 💬",
                parse_mode="HTML"
            )

        logger.info(f"User {user_id} continuing dialog {dialog_id} with {persona_name}")
        break


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
