"""
Upgrades handler - Communication enhancements

Handles upgrades button from main menu.
Shows available upgrades with Telegram Stars pricing.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from shared.database import get_db
from shared.database.services import get_user_by_id, get_subscription_by_user_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="upgrades")


# ==================== TEXTS ====================

UPGRADES_RU = """💗 <b>Улучшения</b>

{status_text}

<b>Режим страсти</b>
Персонаж общается смелее и чувственнее при достаточном доверии.

<b>Фантазии и сцены</b>
Доступ к особым сценариям и фантазиям."""

UPGRADES_EN = """💗 <b>Upgrades</b>

{status_text}

<b>Passion Mode</b>
Character communicates more boldly and sensually with enough trust.

<b>Fantasies & Scenes</b>
Access to special scenarios and fantasies."""

# Status texts
NO_UPGRADES_RU = "Пока нет активных улучшений. Подключи фичи, чтобы сделать общение богаче."
NO_UPGRADES_EN = "No active upgrades yet. Enable features to make conversations richer."

UPGRADES_ACTIVE_RU = "Активные улучшения: {active_list}"
UPGRADES_ACTIVE_EN = "Active upgrades: {active_list}"


# ==================== KEYBOARDS ====================

def get_upgrades_keyboard_ru(intense_active: bool, fantasy_active: bool) -> InlineKeyboardMarkup:
    """Upgrades keyboard (Russian)"""
    buttons = []

    if intense_active:
        buttons.append([InlineKeyboardButton(text="✅ Режим страсти", callback_data="upgrades:intense_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Режим страсти · 150 ⭐", callback_data="upgrades:buy_intense")])

    if fantasy_active:
        buttons.append([InlineKeyboardButton(text="✅ Фантазии и сцены", callback_data="upgrades:fantasy_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Фантазии и сцены · 200 ⭐", callback_data="upgrades:buy_fantasy")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="upgrades:back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_upgrades_keyboard_en(intense_active: bool, fantasy_active: bool) -> InlineKeyboardMarkup:
    """Upgrades keyboard (English)"""
    buttons = []

    if intense_active:
        buttons.append([InlineKeyboardButton(text="✅ Passion Mode", callback_data="upgrades:intense_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Passion Mode · 150 ⭐", callback_data="upgrades:buy_intense")])

    if fantasy_active:
        buttons.append([InlineKeyboardButton(text="✅ Fantasies & Scenes", callback_data="upgrades:fantasy_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Fantasies & Scenes · 200 ⭐", callback_data="upgrades:buy_fantasy")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="upgrades:back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


async def get_user_upgrades(user_id: int) -> dict:
    """
    Get user's active upgrades.

    Returns dict with:
        - intense_mode: bool
        - fantasy_scenes: bool
    """
    async for db in get_db():
        subscription = await get_subscription_by_user_id(db, user_id)
        if subscription:
            # Handle both dict (from cache) and SQLAlchemy object
            if isinstance(subscription, dict):
                return {
                    "intense_mode": subscription.get("intense_mode", False),
                    "fantasy_scenes": subscription.get("fantasy_scenes", False),
                }
            else:
                # Fields may not exist yet - default to False
                return {
                    "intense_mode": getattr(subscription, "intense_mode", False) or False,
                    "fantasy_scenes": getattr(subscription, "fantasy_scenes", False) or False,
                }
    return {"intense_mode": False, "fantasy_scenes": False}


def build_status_text(upgrades: dict, lang: str) -> str:
    """Build status text based on active upgrades"""
    active = []
    if upgrades["intense_mode"]:
        active.append("Режим страсти" if lang == "ru" else "Passion Mode")
    if upgrades["fantasy_scenes"]:
        active.append("Фантазии и сцены" if lang == "ru" else "Fantasies & Scenes")

    if not active:
        return NO_UPGRADES_RU if lang == "ru" else NO_UPGRADES_EN

    active_list = ", ".join(active)
    if lang == "ru":
        return UPGRADES_ACTIVE_RU.format(active_list=active_list)
    else:
        return UPGRADES_ACTIVE_EN.format(active_list=active_list)


# ==================== HANDLERS ====================

async def _show_upgrades_screen(user_id: int, respond_func):
    """Common logic for showing upgrades screen"""
    lang = await get_user_language(user_id)
    upgrades = await get_user_upgrades(user_id)

    status_text = build_status_text(upgrades, lang)

    if lang == "ru":
        text = UPGRADES_RU.format(status_text=status_text)
        keyboard = get_upgrades_keyboard_ru(upgrades["intense_mode"], upgrades["fantasy_scenes"])
    else:
        text = UPGRADES_EN.format(status_text=status_text)
        keyboard = get_upgrades_keyboard_en(upgrades["intense_mode"], upgrades["fantasy_scenes"])

    await respond_func(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} opened upgrades, intense={upgrades['intense_mode']}, fantasy={upgrades['fantasy_scenes']}")


@router.message(Command("upgrades"))
async def cmd_upgrades(message: Message):
    """Handle /upgrades command"""
    await _show_upgrades_screen(message.from_user.id, message.answer)


@router.callback_query(F.data == "menu:upgrades")
async def on_upgrades(callback: CallbackQuery):
    """Handle 'Upgrades' button from main menu"""
    await callback.answer()
    await _show_upgrades_screen(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data == "upgrades:buy_intense")
async def on_buy_intense(callback: CallbackQuery):
    """Handle Passion Mode purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} wants to buy Passion Mode")


@router.callback_query(F.data == "upgrades:buy_fantasy")
async def on_buy_fantasy(callback: CallbackQuery):
    """Handle Fantasies & Scenes purchase"""
    await callback.answer("🚧 Оплата в разработке / Payment coming soon", show_alert=True)
    logger.info(f"User {callback.from_user.id} wants to buy Fantasies & Scenes")


@router.callback_query(F.data == "upgrades:intense_info")
async def on_intense_info(callback: CallbackQuery):
    """Handle Passion Mode info (when already active)"""
    lang = await get_user_language(callback.from_user.id)
    if lang == "ru":
        await callback.answer("✅ Режим страсти активен", show_alert=False)
    else:
        await callback.answer("✅ Passion Mode is active", show_alert=False)


@router.callback_query(F.data == "upgrades:fantasy_info")
async def on_fantasy_info(callback: CallbackQuery):
    """Handle Fantasies & Scenes info (when already active)"""
    lang = await get_user_language(callback.from_user.id)
    if lang == "ru":
        await callback.answer("✅ Фантазии и сцены активны", show_alert=False)
    else:
        await callback.answer("✅ Fantasies & Scenes is active", show_alert=False)


@router.callback_query(F.data == "upgrades:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from upgrades")
