"""
Main menu handler

This is where users land after onboarding or when returning to the bot.
Contains main menu text and webapp button.
"""
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.config import config
from shared.utils import get_logger
from shared.database import get_db, get_user_by_id, User

logger = get_logger(__name__)
router = Router(name="menu")


# ==================== MENU TEXT VARIANTS ====================

# Variant 1 - "She missed you" (waiting)
MENU_VARIANT_1_RU = """Vitte 💜

Она скучала.

Готова продолжить с того места,
где вы остановились.

Или начать что-то новое.
Как захочешь."""

MENU_VARIANT_1_EN = """Vitte 💜

She missed you.

Ready to continue from where
you left off.

Or start something new.
Whatever you want."""

# Variant 2 - "She's online" (available)
MENU_VARIANT_2_RU = """💜 Vitte

Она онлайн.
Ждёт твоего сообщения.

Можешь просто поболтать.
Можешь пофлиртовать.
Можешь попросить большего.

Решать тебе."""

MENU_VARIANT_2_EN = """💜 Vitte

She's online.
Waiting for your message.

You can just chat.
You can flirt.
You can ask for more.

It's up to you."""

# Variant 3 - "Your girl is waiting" (hot & short)
MENU_VARIANT_3_RU = """Vitte 💜

Твоя девочка ждёт.

Напиши ей.
Она уже думает о тебе."""

MENU_VARIANT_3_EN = """Vitte 💜

Your girl is waiting.

Text her.
She's already thinking about you."""

# Lists for random selection
MENU_VARIANTS_RU = [MENU_VARIANT_1_RU, MENU_VARIANT_2_RU, MENU_VARIANT_3_RU]
MENU_VARIANTS_EN = [MENU_VARIANT_1_EN, MENU_VARIANT_2_EN, MENU_VARIANT_3_EN]


# ==================== WELCOME TEXT (FIRST TIME) ====================

WELCOME_TEXT_RU = """Добро пожаловать в Vitte 💜

Здесь тебя уже ждут. Это пространство для тёплых переписок, флирта и близости — с AI-персонажами, которые умеют слушать и отвечать по-настоящему.

Героини с уникальными историями. Пиши когда хочется, открывай фото, включай режим страсти. Всё между вами."""

WELCOME_TEXT_EN = """Welcome to Vitte 💜

They're already waiting for you here. This is a space for warm conversations, flirting and intimacy — with AI characters who truly know how to listen and respond.

Heroines with unique stories. Write whenever you want, unlock photos, turn on passion mode. Everything stays between you."""


# ==================== FEATURE NAMES ====================

FEATURE_NAMES_RU = {
    "intense_mode": "Интенсив",
    "fantasy_scenes": "Фантазии"
}

FEATURE_NAMES_EN = {
    "intense_mode": "Intense",
    "fantasy_scenes": "Fantasy"
}


# ==================== USER STATUS ====================

async def get_user_status(user_id: int) -> dict:
    """
    Get user's subscription, messages, images and features status
    Returns dict with status data for menu display
    """
    status = {
        "subscription": "Free",
        "messages_today": 0,
        "images_remaining": 0,
        "features": []
    }

    try:
        async for db in get_db():
            result = await db.execute(
                select(User)
                .options(
                    selectinload(User.subscription),
                    selectinload(User.image_balance),
                    selectinload(User.feature_unlocks)
                )
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                break

            # Subscription status
            subscription = user.subscription
            has_active_sub = bool(
                subscription and
                subscription.is_active and
                subscription.expires_at and
                subscription.expires_at > datetime.utcnow()
            )
            status["subscription"] = "Premium" if has_active_sub else "Free"

            # Messages today (free messages used)
            status["messages_today"] = user.free_messages_used or 0

            # Images remaining
            image_balance = user.image_balance
            if image_balance:
                status["images_remaining"] = image_balance.remaining_purchased_images or 0

            # Active features
            if user.feature_unlocks:
                for f in user.feature_unlocks:
                    if f.enabled:
                        status["features"].append(f.feature_code)

            break

    except Exception as e:
        logger.error(f"Error getting user status: {e}")

    return status


def build_status_block(status: dict, lang: str = "ru", include_cta: bool = True) -> str:
    """Build the status monitoring block for menu

    Args:
        status: User status dict
        lang: Language code
        include_cta: Include call-to-action text at the end
    """
    feature_names = FEATURE_NAMES_RU if lang == "ru" else FEATURE_NAMES_EN

    # Format features
    if status["features"]:
        features_str = ", ".join(
            feature_names.get(f, f) for f in status["features"]
        )
    else:
        features_str = "нет" if lang == "ru" else "none"

    if lang == "ru":
        block = f"""💎 Подписка: {status["subscription"]}
💬 Сообщений сегодня: {status["messages_today"]}
🖼 Изображений: {status["images_remaining"]}
✨ Улучшения: {features_str}"""
        if include_cta:
            block += "\n\nНаписать ей 💌"
        else:
            block += "\n\nЖми «Открыть Vitte 💌» — выбери ту, с кем хочешь познакомиться."
    else:
        block = f"""💎 Subscription: {status["subscription"]}
💬 Messages today: {status["messages_today"]}
🖼 Images: {status["images_remaining"]}
✨ Enhancements: {features_str}"""
        if include_cta:
            block += "\n\nText her 💌"
        else:
            block += "\n\nTap «Open Vitte 💌» — choose who you want to meet."

    return block


# ==================== KEYBOARDS ====================

def get_main_menu_keyboard_ru() -> InlineKeyboardMarkup:
    """Main menu keyboard (Russian)"""
    # WebApp button or fallback
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="💌 Открыть Vitte",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="💌 Открыть Vitte",
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

async def show_main_menu(target, lang: str = "ru", user_id: int = None, is_welcome: bool = False):
    """
    Show main menu to user (always sends new message)

    Args:
        target: Message or CallbackQuery to respond to
        lang: Language code ('ru' or 'en')
        user_id: Telegram user ID for status fetching
        is_welcome: If True, show welcome message for first-time users
    """
    # Get user_id from target if not provided
    if user_id is None:
        if hasattr(target, 'from_user'):
            user_id = target.from_user.id
        elif hasattr(target, 'message') and hasattr(target.message, 'from_user'):
            user_id = target.message.from_user.id

    # Get user status
    status = await get_user_status(user_id) if user_id else {
        "subscription": "Free",
        "messages_today": 0,
        "images_remaining": 0,
        "features": []
    }

    if is_welcome:
        # Welcome message for first-time users
        welcome_text = WELCOME_TEXT_RU if lang == "ru" else WELCOME_TEXT_EN
        status_block = build_status_block(status, lang, include_cta=False)
        text = welcome_text + "\n\n" + status_block

        # Mark user as having seen welcome
        await mark_welcome_seen(user_id)
    else:
        # Random text variant for returning users
        variants = MENU_VARIANTS_RU if lang == "ru" else MENU_VARIANTS_EN
        menu_text = random.choice(variants)
        status_block = build_status_block(status, lang, include_cta=True)
        text = menu_text + "\n\n" + status_block

    keyboard = get_main_menu_keyboard_ru() if lang == "ru" else get_main_menu_keyboard_en()

    if hasattr(target, 'message'):
        # CallbackQuery - send new message
        await target.message.answer(text, reply_markup=keyboard)
    else:
        # Message object
        await target.answer(text, reply_markup=keyboard)


async def mark_welcome_seen(user_id: int) -> None:
    """Mark user as having seen the welcome message"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.has_seen_welcome = True
                await db.commit()
                logger.info(f"Marked has_seen_welcome=True for user {user_id}")
            break
    except Exception as e:
        logger.error(f"Error marking welcome seen for user {user_id}: {e}")


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
