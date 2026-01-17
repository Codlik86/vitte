"""
Shop handler - Image packs store

Handles shop button from main menu.
Shows available image packs with Telegram Stars pricing.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from shared.database import get_db
from shared.database.services import get_user_by_id, get_subscription_by_user_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="shop")


# ==================== TEXTS ====================

SHOP_RU = """🖼 <b>Изображения</b>

У тебя <b>{images_count}</b> изображений.
Докупи ещё — выбери нужный пакет ниже."""

SHOP_EN = """🖼 <b>Images</b>

You have <b>{images_count}</b> images.
Buy more — choose a pack below."""


# ==================== KEYBOARDS ====================

def get_shop_keyboard_ru() -> InlineKeyboardMarkup:
    """Image packs keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="20 изображений — 50 ⭐", callback_data="shop:pack_20"),
        ],
        [
            InlineKeyboardButton(text="50 изображений — 120 ⭐", callback_data="shop:pack_50"),
        ],
        [
            InlineKeyboardButton(text="100 изображений — 250 ⭐", callback_data="shop:pack_100"),
        ],
        [
            InlineKeyboardButton(text="200 изображений — 500 ⭐", callback_data="shop:pack_200"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="shop:back_to_menu"),
        ]
    ])


def get_shop_keyboard_en() -> InlineKeyboardMarkup:
    """Image packs keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="20 images — 50 ⭐", callback_data="shop:pack_20"),
        ],
        [
            InlineKeyboardButton(text="50 images — 120 ⭐", callback_data="shop:pack_50"),
        ],
        [
            InlineKeyboardButton(text="100 images — 250 ⭐", callback_data="shop:pack_100"),
        ],
        [
            InlineKeyboardButton(text="200 images — 500 ⭐", callback_data="shop:pack_200"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="shop:back_to_menu"),
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


async def get_user_images_count(user_id: int) -> int:
    """Get remaining images count for user"""
    async for db in get_db():
        subscription = await get_subscription_by_user_id(db, user_id)
        if subscription:
            # Handle both dict (from cache) and SQLAlchemy object
            if isinstance(subscription, dict):
                images_limit = subscription.get("images_limit", 0)
                images_used = subscription.get("images_used", 0)
            else:
                images_limit = subscription.images_limit or 0
                images_used = subscription.images_used or 0
            return max(0, images_limit - images_used)
    return 0


# ==================== HANDLERS ====================

@router.callback_query(F.data == "menu:shop")
async def on_shop(callback: CallbackQuery):
    """Handle 'Shop' button from main menu"""
    await callback.answer()
    user_id = callback.from_user.id

    # Get user language and images count
    lang = await get_user_language(user_id)
    images_count = await get_user_images_count(user_id)

    if lang == "ru":
        text = SHOP_RU.format(images_count=images_count)
        keyboard = get_shop_keyboard_ru()
    else:
        text = SHOP_EN.format(images_count=images_count)
        keyboard = get_shop_keyboard_en()

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    logger.info(f"User {user_id} opened shop, images: {images_count}")


@router.callback_query(F.data == "shop:pack_20")
async def on_pack_20(callback: CallbackQuery):
    """Handle 20 images pack purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} selected 20 images pack")


@router.callback_query(F.data == "shop:pack_50")
async def on_pack_50(callback: CallbackQuery):
    """Handle 50 images pack purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} selected 50 images pack")


@router.callback_query(F.data == "shop:pack_100")
async def on_pack_100(callback: CallbackQuery):
    """Handle 100 images pack purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} selected 100 images pack")


@router.callback_query(F.data == "shop:pack_200")
async def on_pack_200(callback: CallbackQuery):
    """Handle 200 images pack purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} selected 200 images pack")


@router.callback_query(F.data == "shop:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from shop")
