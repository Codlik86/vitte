"""
Subscription handler - Premium subscription options

Handles subscription button from main menu.
Shows Vitte Premium plans with Telegram Stars pricing.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from shared.database import get_db
from shared.database.services import get_user_by_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="subscription")


# ==================== TEXTS ====================

SUBSCRIPTION_RU = """💎 <b>Vitte Premium</b>

• Безлимитные сообщения
• 20 изображений каждый день
• Самые продвинутые модели ИИ
• Мгновенные ответы и качественные изображения

Выбери подходящий план:"""

SUBSCRIPTION_EN = """💎 <b>Vitte Premium</b>

• Unlimited messages
• 20 images every day
• Most advanced AI models
• Instant responses and quality images

Choose your plan:"""


# ==================== KEYBOARDS ====================

def get_subscription_keyboard_ru() -> InlineKeyboardMarkup:
    """Subscription plans keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Vitte Plus 2 дня — 199 ⭐", callback_data="sub:plus_2d"),
        ],
        [
            InlineKeyboardButton(text="Vitte Plus 7 дней — 399 ⭐", callback_data="sub:plus_7d"),
        ],
        [
            InlineKeyboardButton(text="Vitte Plus 30 дней — 999 ⭐", callback_data="sub:plus_30d"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="sub:back_to_menu"),
        ]
    ])


def get_subscription_keyboard_en() -> InlineKeyboardMarkup:
    """Subscription plans keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Vitte Plus 2 days — 199 ⭐", callback_data="sub:plus_2d"),
        ],
        [
            InlineKeyboardButton(text="Vitte Plus 7 days — 399 ⭐", callback_data="sub:plus_7d"),
        ],
        [
            InlineKeyboardButton(text="Vitte Plus 30 days — 999 ⭐", callback_data="sub:plus_30d"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="sub:back_to_menu"),
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

async def _show_subscription_screen(user_id: int, respond_func):
    """Common logic for showing subscription screen"""
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = SUBSCRIPTION_RU
        keyboard = get_subscription_keyboard_ru()
    else:
        text = SUBSCRIPTION_EN
        keyboard = get_subscription_keyboard_en()

    await respond_func(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} opened subscription menu")


@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    """Handle /subscription command"""
    await _show_subscription_screen(message.from_user.id, message.answer)


@router.callback_query(F.data == "menu:subscription")
async def on_subscription(callback: CallbackQuery):
    """Handle 'Subscription' button from main menu"""
    await callback.answer()
    await _show_subscription_screen(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data == "sub:plus_2d")
async def on_sub_2d(callback: CallbackQuery):
    """Handle 2-day subscription purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)

    logger.info(f"User {callback.from_user.id} selected Vitte Plus 2 days")


@router.callback_query(F.data == "sub:plus_7d")
async def on_sub_7d(callback: CallbackQuery):
    """Handle 7-day subscription purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)

    logger.info(f"User {callback.from_user.id} selected Vitte Plus 7 days")


@router.callback_query(F.data == "sub:plus_30d")
async def on_sub_30d(callback: CallbackQuery):
    """Handle 30-day subscription purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)

    logger.info(f"User {callback.from_user.id} selected Vitte Plus 30 days")


@router.callback_query(F.data == "sub:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from subscription")
