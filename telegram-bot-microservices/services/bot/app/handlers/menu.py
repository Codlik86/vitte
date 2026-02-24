"""
Main menu handler

This is where users land after onboarding or when returning to the bot.
Contains main menu text and webapp button.
"""
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, InputMediaPhoto
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.config import config
from shared.utils import get_logger
from shared.utils.redis import redis_client
from shared.database import get_db, get_user_by_id, User

logger = get_logger(__name__)
router = Router(name="menu")


# ==================== MENU TEXT VARIANTS ====================

# Variant 1
MENU_VARIANT_1_RU = """Добро пожаловать в CraveMe 💜

Выбери персонажа и начни
приватную беседу."""

MENU_VARIANT_1_EN = """Welcome to CraveMe 💜

Choose a character and start
a private conversation."""

# Variant 2
MENU_VARIANT_2_RU = """Твое личное пространство 💜

Кого выберешь сегодня?"""

MENU_VARIANT_2_EN = """Your personal space 💜

Who will you choose today?"""

# Variant 3
MENU_VARIANT_3_RU = """CraveMe 💜

Выбери персонажа или продолжи
диалог с того места, где остановился."""

MENU_VARIANT_3_EN = """CraveMe 💜

Choose a character or continue
the dialog from where you left off."""

# Variant 4
MENU_VARIANT_4_RU = """CraveMe 💜

Время для приватной беседы.
Новый персонаж или продолжить?"""

MENU_VARIANT_4_EN = """CraveMe 💜

Time for a private conversation.
New character or continue?"""

# Variant 5
MENU_VARIANT_5_RU = """CraveMe 💜

Выбери персонажа и начни чат."""

MENU_VARIANT_5_EN = """CraveMe 💜

Choose a character and start chatting."""

# Lists for random selection
MENU_VARIANTS_RU = [MENU_VARIANT_1_RU, MENU_VARIANT_2_RU, MENU_VARIANT_3_RU, MENU_VARIANT_4_RU, MENU_VARIANT_5_RU]
MENU_VARIANTS_EN = [MENU_VARIANT_1_EN, MENU_VARIANT_2_EN, MENU_VARIANT_3_EN, MENU_VARIANT_4_EN, MENU_VARIANT_5_EN]

# Aliases for backward compatibility (random choice)
MAIN_MENU_TEXT_RU = random.choice(MENU_VARIANTS_RU)
MAIN_MENU_TEXT_EN = random.choice(MENU_VARIANTS_EN)


# ==================== WELCOME TEXT (FIRST TIME) ====================

WELCOME_TEXT_RU = """Добро пожаловать в CraveMe 💜

Приватное пространство для флирта
с AI-персонажами.

Уникальные героини, фото, режим страсти.
Всё между вами."""

WELCOME_TEXT_EN = """Welcome to CraveMe 💜

Private space for flirting
with AI characters.

Unique heroines, photos, passion mode.
Everything stays between you."""


# ==================== FEATURE NAMES ====================

FEATURE_NAMES_RU = {
    "intense_mode": "Интенсив"
}

FEATURE_NAMES_EN = {
    "intense_mode": "Intense"
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
                subscription.expires_at > datetime.now(timezone.utc)
            )
            status["subscription"] = "Premium" if has_active_sub else "Free"

            # Messages today - get from Redis
            try:
                redis_key = f"user:{user_id}:messages:daily"
                current_count = await redis_client.get(redis_key)
                status["messages_today"] = int(current_count) if current_count else 0
            except Exception as e:
                logger.error(f"Error getting message count from Redis: {e}")
                status["messages_today"] = 0

            # Images remaining (purchased + daily quota)
            image_balance = user.image_balance
            if image_balance:
                # Calculate remaining from daily quota (for Premium users)
                remaining_daily = max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used)
                remaining_purchased = image_balance.remaining_purchased_images or 0
                status["images_remaining"] = remaining_daily + remaining_purchased
            else:
                status["images_remaining"] = 0

            # Active features
            if user.feature_unlocks:
                for f in user.feature_unlocks:
                    if f.enabled:
                        status["features"].append(f.feature_code)

            break

    except Exception as e:
        logger.error(f"Error getting user status: {e}")

    return status


def build_status_block(status: dict, lang: str = "ru") -> str:
    """Build the status monitoring block for menu

    Args:
        status: User status dict
        lang: Language code
    """
    plan = status["subscription"]
    is_premium = plan == "Premium"
    feature_names = FEATURE_NAMES_RU if lang == "ru" else FEATURE_NAMES_EN

    # Format features - ОТКЛЮЧЕНО, больше не показываем улучшения
    # if status["features"]:
    #     features_str = ", ".join(
    #         feature_names.get(f, f) for f in status["features"]
    #     )
    # else:
    #     features_str = "Нет улучшений" if lang == "ru" else "No upgrades"

    # Images
    images_remaining = status["images_remaining"]
    images_str = f"🖼 {images_remaining} доступно" if lang == "ru" else f"🖼 {images_remaining} available"

    if is_premium:
        # Premium user - show unlimited messages + images (БЕЗ улучшений)
        if lang == "ru":
            block = f"""💎 Premium
💬 Безлимит
{images_str}"""
        else:
            block = f"""💎 Premium
💬 Unlimited
{images_str}"""
    else:
        # Free user - show full status with limits (вертикально)
        messages_today = status["messages_today"]
        messages_limit = 20
        messages_str = f"💬 {messages_limit - messages_today}/{messages_limit}"

        if lang == "ru":
            block = f"""👤 Free
{messages_str}
{images_str}"""
        else:
            block = f"""👤 Free
{messages_str}
{images_str}"""

    return block


# ==================== KEYBOARDS ====================

def get_main_menu_keyboard_ru() -> InlineKeyboardMarkup:
    """Main menu keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Начать", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💎 Подписка", callback_data="menu:subscription"),
        ],
        [
            InlineKeyboardButton(text="🛍 Магазин", callback_data="menu:shop"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ]
    ])


def get_main_menu_keyboard_en() -> InlineKeyboardMarkup:
    """Main menu keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Start", callback_data="menu:start_chat"),
            InlineKeyboardButton(text="💎 Subscription", callback_data="menu:subscription"),
        ],
        [
            InlineKeyboardButton(text="🛍 Shop", callback_data="menu:shop"),
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
        status_block = build_status_block(status, lang)
        text = welcome_text + "\n\n" + status_block

        # Mark user as having seen welcome
        await mark_welcome_seen(user_id)
    else:
        # Random text variant for returning users
        variants = MENU_VARIANTS_RU if lang == "ru" else MENU_VARIANTS_EN
        menu_text = random.choice(variants)
        status_block = build_status_block(status, lang)
        text = menu_text + "\n\n" + status_block

    keyboard = get_main_menu_keyboard_ru() if lang == "ru" else get_main_menu_keyboard_en()

    # Random menu photo (1 of 3)
    menu_photo_url = f"https://craveme.tech/storage/menu-pics/menu/{random.randint(1, 3):03d}.png"

    # Send menu with photo
    if hasattr(target, 'message'):
        # CallbackQuery - send new message with photo
        await target.message.answer_photo(
            photo=menu_photo_url,
            caption=text,
            reply_markup=keyboard
        )
    else:
        # Message object - send photo
        await target.answer_photo(
            photo=menu_photo_url,
            caption=text,
            reply_markup=keyboard
        )


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
            if user:
                lang = user.get("language_code") if isinstance(user, dict) else user.language_code
                if lang:
                    return lang
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
            text = "💌 Нажми на кнопку, чтобы открыть приложение CraveMe"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть CraveMe 💜", web_app=WebAppInfo(url=config.webapp_url))]
            ])
        else:
            text = "💌 Tap the button to open CraveMe app"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Open CraveMe 💜", web_app=WebAppInfo(url=config.webapp_url))]
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
    logger.info(f"User {callback.from_user.id} clicked Open CraveMe button")


@router.callback_query(F.data == "menu:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle back to main menu button click"""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    await show_main_menu(callback, lang=lang, user_id=callback.from_user.id)
    logger.info(f"User {callback.from_user.id} returned to main menu")
