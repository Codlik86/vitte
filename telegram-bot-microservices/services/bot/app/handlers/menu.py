"""
Main menu handler

This is where users land after onboarding or when returning to the bot.
Contains main menu text and webapp button.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from shared.utils import get_logger

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
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💕 Начать общение", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💖 Подписка", callback_data="menu:subscription"),
        ],
        [
            InlineKeyboardButton(text="💌 Открыть приложение", callback_data="menu:open_webapp"),
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
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💕 Start Chat", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💖 Subscription", callback_data="menu:subscription"),
        ],
        [
            InlineKeyboardButton(text="💌 Open App", callback_data="menu:open_webapp"),
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


# ==================== HANDLERS ====================

@router.callback_query(F.data == "menu:open_webapp")
async def on_open_webapp(callback: CallbackQuery):
    """Handle webapp button click"""
    await callback.answer("🚧 Web App в разработке / Web App under development", show_alert=True)

    logger.info(f"User {callback.from_user.id} clicked Open Vitte button")
