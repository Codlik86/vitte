"""
Main menu handler

This is where users land after onboarding or when returning to the bot.
Contains main menu text and webapp button.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

from app.config import config
from shared.utils import get_logger
from shared.database import get_db, get_user_by_id

logger = get_logger(__name__)
router = Router(name="menu")


# ==================== TEXTS ====================

MAIN_MENU_RU = """Добро пожаловать в Vitte 💜

Это романтический AI-компаньон, который всегда на связи: можно делиться мыслями, получать тёплый отклик и переписываться как с онлайн-партнёром.

В мини-приложении удобно выбирать героиню, оформлять подписку и включать улучшения общения.

Есть ежедневный бесплатный лимит сообщений и расширенный доступ по подписке.

Чтобы продолжить, нажми «Открыть Vitte 💌» или воспользуйся командами в правом меню."""

MAIN_MENU_EN = """Welcome to Vitte 💜

This is a romantic AI companion that's always online: share your thoughts, get warm responses, and chat like with an online partner.

In the mini-app you can choose your character, manage subscription and enable communication enhancements.

There's a free daily message limit and extended access with subscription.

To continue, tap "Open Vitte 💌" or use the commands in the right menu."""


# ==================== KEYBOARDS ====================

def get_main_menu_keyboard_ru() -> InlineKeyboardMarkup:
    """Main menu keyboard (Russian)"""
    # WebApp button or fallback
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="💌 Открыть приложение",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="💌 Открыть приложение",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💕 Начать общение", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💖 Подписка", callback_data="menu:subscription"),
        ],
        [
            webapp_btn,
        ],
        [
            InlineKeyboardButton(text="💝 Магазин", callback_data="menu:shop"),
            InlineKeyboardButton(text="💗 Улучшения", callback_data="menu:upgrades"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Основные настройки", callback_data="menu:settings"),
        ]
    ])


def get_main_menu_keyboard_en() -> InlineKeyboardMarkup:
    """Main menu keyboard (English)"""
    # WebApp button or fallback
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="💌 Open App",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="💌 Open App",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💕 Start Chat", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💖 Subscription", callback_data="menu:subscription"),
        ],
        [
            webapp_btn,
        ],
        [
            InlineKeyboardButton(text="💝 Shop", callback_data="menu:shop"),
            InlineKeyboardButton(text="💗 Upgrades", callback_data="menu:upgrades"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu:settings"),
        ]
    ])


# ==================== HELPER FUNCTIONS ====================

async def show_main_menu(target, lang: str = "ru"):
    """
    Show main menu to user (always sends new message)

    Args:
        target: Message or CallbackQuery to respond to
        lang: Language code ('ru' or 'en')
    """
    text = MAIN_MENU_RU if lang == "ru" else MAIN_MENU_EN
    keyboard = get_main_menu_keyboard_ru() if lang == "ru" else get_main_menu_keyboard_en()

    if hasattr(target, 'message'):
        # CallbackQuery - send new message
        await target.message.answer(text, reply_markup=keyboard)
    else:
        # Message object
        await target.answer(text, reply_markup=keyboard)


# ==================== HELPER FUNCTIONS ====================

async def get_user_language(user_id: int) -> str:
    """Get user's preferred language from database"""
    try:
        async for db in get_db():
            user = await get_user_by_id(db, user_id)
            if user and user.language_code:
                return user.language_code
            break
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
    return "ru"


# ==================== HANDLERS ====================

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Handle /menu command - show main menu"""
    lang = await get_user_language(message.from_user.id)
    await show_main_menu(message, lang=lang)
    logger.info(f"User {message.from_user.id} opened main menu via /menu command")


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Handle /app command - open webapp"""
    lang = await get_user_language(message.from_user.id)

    if config.webapp_url:
        # WebApp is configured - show button to open it
        if lang == "ru":
            text = "💌 Нажми на кнопку, чтобы открыть приложение Vitte"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть Vitte 💜", web_app=WebAppInfo(url=config.webapp_url))]
            ])
        else:
            text = "💌 Tap the button to open Vitte app"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Open Vitte 💜", web_app=WebAppInfo(url=config.webapp_url))]
            ])
        await message.answer(text, reply_markup=keyboard)
    else:
        # WebApp not configured
        if lang == "ru":
            await message.answer("🚧 Web App в разработке")
        else:
            await message.answer("🚧 Web App under development")

    logger.info(f"User {message.from_user.id} opened app via /app command")


@router.callback_query(F.data == "menu:open_webapp")
async def on_open_webapp(callback: CallbackQuery):
    """Handle webapp button click (fallback when webapp_url not configured)"""
    await callback.answer("🚧 Web App в разработке / Web App under development", show_alert=True)
    logger.info(f"User {callback.from_user.id} clicked Open Vitte button")
