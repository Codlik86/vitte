"""
Upgrades handler - Communication enhancements

Handles upgrades button from main menu.
Shows available upgrades with Telegram Stars pricing.
"""
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from datetime import datetime

from shared.database import get_db, User, FeatureUnlock, Purchase, Subscription
from shared.database.services import get_user_by_id, get_subscription_by_user_id
from shared.utils import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
router = Router(name="upgrades")


# ==================== UPGRADES CONFIG ====================

UPGRADES = {
    "intense_mode": {
        "name_ru": "Интенсивный режим",
        "name_en": "Intense Mode",
        "description_ru": "Более эмоциональные и глубокие ответы персонажей",
        "description_en": "More emotional and deeper character responses",
        "price_stars": 200,
        "product_code": "upgrade_intense_mode",
        "feature_code": "intense_mode"
    },
    "fantasy_scenes": {
        "name_ru": "Фантазийные сцены",
        "name_en": "Fantasy Scenes",
        "description_ru": "Разблокирует расширенные сценарии и истории",
        "description_en": "Unlocks extended scenarios and stories",
        "price_stars": 200,
        "product_code": "upgrade_fantasy_scenes",
        "feature_code": "fantasy_scenes"
    }
}


# ==================== TEXTS ====================

UPGRADES_RU = """💗 <b>Улучшения</b>

{status_text}

<b>Интенсивный режим</b>
Более эмоциональные и глубокие ответы персонажей.

<b>Фантазийные сцены</b>
Разблокирует расширенные сценарии и истории."""

UPGRADES_EN = """💗 <b>Upgrades</b>

{status_text}

<b>Intense Mode</b>
More emotional and deeper character responses.

<b>Fantasy Scenes</b>
Unlocks extended scenarios and stories."""

# Status texts
NO_UPGRADES_RU = "Пока нет активных улучшений. Подключи фичи, чтобы сделать общение богаче."
NO_UPGRADES_EN = "No active upgrades yet. Enable features to make conversations richer."

UPGRADES_ACTIVE_RU = "Активные улучшения: {active_list}"
UPGRADES_ACTIVE_EN = "Active upgrades: {active_list}"


PAYMENT_METHOD_RU = """💳 <b>Выбери способ оплаты</b>

Ты выбрал: <b>{upgrade_name}</b>
Стоимость: <b>{price} ⭐</b>

{description}

Как будешь оплачивать?"""

PAYMENT_METHOD_EN = """💳 <b>Choose payment method</b>

You selected: <b>{upgrade_name}</b>
Price: <b>{price} ⭐</b>

{description}

How would you like to pay?"""


# ==================== KEYBOARDS ====================

def get_upgrades_keyboard_ru(intense_active: bool, fantasy_active: bool) -> InlineKeyboardMarkup:
    """Upgrades keyboard (Russian)"""
    buttons = []

    if intense_active:
        buttons.append([InlineKeyboardButton(text="✅ Интенсивный режим", callback_data="upgrades:intense_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Интенсивный режим · 200 ⭐", callback_data="upgrades:buy_intense_mode")])

    if fantasy_active:
        buttons.append([InlineKeyboardButton(text="✅ Фантазийные сцены", callback_data="upgrades:fantasy_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Фантазийные сцены · 200 ⭐", callback_data="upgrades:buy_fantasy_scenes")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="upgrades:back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_upgrades_keyboard_en(intense_active: bool, fantasy_active: bool) -> InlineKeyboardMarkup:
    """Upgrades keyboard (English)"""
    buttons = []

    if intense_active:
        buttons.append([InlineKeyboardButton(text="✅ Intense Mode", callback_data="upgrades:intense_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Intense Mode · 200 ⭐", callback_data="upgrades:buy_intense_mode")])

    if fantasy_active:
        buttons.append([InlineKeyboardButton(text="✅ Fantasy Scenes", callback_data="upgrades:fantasy_info")])
    else:
        buttons.append([InlineKeyboardButton(text="Fantasy Scenes · 200 ⭐", callback_data="upgrades:buy_fantasy_scenes")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="upgrades:back_to_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_method_keyboard_ru(upgrade_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"upgrades_pay:stars:{upgrade_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к улучшениям", callback_data="upgrades:back_to_list"),
        ]
    ])


def get_payment_method_keyboard_en(upgrade_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"upgrades_pay:stars:{upgrade_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back to upgrades", callback_data="upgrades:back_to_list"),
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


async def get_user_upgrades(user_id: int) -> dict:
    """
    Get user's active upgrades from FeatureUnlock table.

    Returns dict with:
        - intense_mode: bool
        - fantasy_scenes: bool
    """
    upgrades = {"intense_mode": False, "fantasy_scenes": False}

    async for db in get_db():
        # Check FeatureUnlock table
        result = await db.execute(
            select(FeatureUnlock).where(
                FeatureUnlock.user_id == user_id,
                FeatureUnlock.enabled == True
            )
        )
        feature_unlocks = result.scalars().all()

        for unlock in feature_unlocks:
            if unlock.feature_code == "intense_mode":
                upgrades["intense_mode"] = True
            elif unlock.feature_code == "fantasy_scenes":
                upgrades["fantasy_scenes"] = True

        # Also check Subscription table for legacy support
        subscription = await get_subscription_by_user_id(db, user_id)
        if subscription:
            if isinstance(subscription, dict):
                if subscription.get("intense_mode"):
                    upgrades["intense_mode"] = True
                if subscription.get("fantasy_scenes"):
                    upgrades["fantasy_scenes"] = True
            else:
                if getattr(subscription, "intense_mode", False):
                    upgrades["intense_mode"] = True
                if getattr(subscription, "fantasy_scenes", False):
                    upgrades["fantasy_scenes"] = True

        break

    return upgrades


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


@router.callback_query(F.data.startswith("upgrades:buy_"))
async def on_select_upgrade(callback: CallbackQuery):
    """Handle upgrade selection - show payment method"""
    await callback.answer()

    # Extract upgrade_id from callback data (upgrades:buy_intense_mode -> intense_mode)
    upgrade_id = callback.data.replace("upgrades:buy_", "")
    upgrade = UPGRADES.get(upgrade_id)

    if not upgrade:
        await callback.answer("❌ Улучшение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = PAYMENT_METHOD_RU.format(
            upgrade_name=upgrade["name_ru"],
            price=upgrade["price_stars"],
            description=upgrade["description_ru"]
        )
        keyboard = get_payment_method_keyboard_ru(upgrade_id)
    else:
        text = PAYMENT_METHOD_EN.format(
            upgrade_name=upgrade["name_en"],
            price=upgrade["price_stars"],
            description=upgrade["description_en"]
        )
        keyboard = get_payment_method_keyboard_en(upgrade_id)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} selected upgrade {upgrade_id}, showing payment methods")


@router.callback_query(F.data == "upgrades:back_to_list")
async def on_back_to_list(callback: CallbackQuery):
    """Handle 'Back to upgrades' button"""
    await callback.answer()
    await _show_upgrades_screen(callback.from_user.id, callback.message.answer)


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


# ==================== PAYMENT HANDLERS ====================

@router.callback_query(F.data.startswith("upgrades_pay:stars:"))
async def on_pay_with_stars(callback: CallbackQuery, bot: Bot):
    """Handle Telegram Stars payment - send invoice"""
    await callback.answer()

    # Extract upgrade_id from callback data (upgrades_pay:stars:intense_mode -> intense_mode)
    upgrade_id = callback.data.replace("upgrades_pay:stars:", "")
    upgrade = UPGRADES.get(upgrade_id)

    if not upgrade:
        await callback.answer("❌ Улучшение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # Check if already purchased
    user_upgrades = await get_user_upgrades(user_id)
    if user_upgrades.get(upgrade_id):
        if lang == "ru":
            await callback.answer("✅ Это улучшение уже активно!", show_alert=True)
        else:
            await callback.answer("✅ This upgrade is already active!", show_alert=True)
        return

    # Create invoice
    upgrade_name = upgrade["name_ru"] if lang == "ru" else upgrade["name_en"]
    description = upgrade["description_ru"] if lang == "ru" else upgrade["description_en"]

    title = f"✨ {upgrade_name}"

    # Create keyboard with Pay button (must be first!) and Main Menu button
    pay_button_text = f"⭐ Оплатить {upgrade['price_stars']} Stars" if lang == "ru" else f"⭐ Pay {upgrade['price_stars']} Stars"
    menu_button_text = "🏠 Главное меню" if lang == "ru" else "🏠 Main Menu"

    invoice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_button_text, pay=True)],  # Pay button must be first!
        [InlineKeyboardButton(text=menu_button_text, callback_data="upgrades:back_to_menu")]
    ])

    # Send invoice
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=f"upgrade:{upgrade_id}:{user_id}",
        currency="XTR",  # Telegram Stars currency code
        prices=[LabeledPrice(label=upgrade_name, amount=upgrade["price_stars"])],
        reply_markup=invoice_keyboard
    )

    logger.info(f"User {user_id} initiated Stars payment for upgrade {upgrade_id}")


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout query - validate the purchase"""
    # Check if this is an upgrade purchase
    if not pre_checkout_query.invoice_payload.startswith("upgrade:"):
        return  # Let other handlers process it

    # Always accept for now (can add validation logic later)
    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id} (upgrade)")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    """Handle successful payment - activate upgrade"""
    payment = message.successful_payment
    user_id = message.from_user.id

    # Check if this is an upgrade purchase
    if not payment.invoice_payload.startswith("upgrade:"):
        return  # Let other handlers process it

    # Parse payload
    payload_parts = payment.invoice_payload.split(":")
    if len(payload_parts) < 2:
        logger.error(f"Invalid payment payload: {payment.invoice_payload}")
        return

    upgrade_id = payload_parts[1]  # upgrade:intense_mode:user_id -> intense_mode
    upgrade = UPGRADES.get(upgrade_id)

    if not upgrade:
        logger.error(f"Unknown upgrade in payment: {upgrade_id}")
        return

    lang = await get_user_language(user_id)

    # Activate upgrade in database
    async for db in get_db():
        # Get user
        user = await db.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found for payment")
            return

        # Check if already unlocked
        result = await db.execute(
            select(FeatureUnlock).where(
                FeatureUnlock.user_id == user_id,
                FeatureUnlock.feature_code == upgrade["feature_code"]
            )
        )
        existing_unlock = result.scalar_one_or_none()

        if existing_unlock:
            # Already unlocked, just enable it
            existing_unlock.enabled = True
        else:
            # Create new feature unlock
            feature_unlock = FeatureUnlock(
                user_id=user_id,
                feature_code=upgrade["feature_code"],
                enabled=True
            )
            db.add(feature_unlock)

        # Also update Subscription for legacy support
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            if upgrade_id == "intense_mode":
                subscription.intense_mode = True
            elif upgrade_id == "fantasy_scenes":
                subscription.fantasy_scenes = True

        # Record purchase
        purchase = Purchase(
            user_id=user_id,
            product_code=upgrade["product_code"],
            provider="telegram_stars",
            amount=upgrade["price_stars"],
            currency="XTR",
            status="success",
            meta={
                "telegram_payment_charge_id": payment.telegram_payment_charge_id,
                "provider_payment_charge_id": payment.provider_payment_charge_id,
                "feature_code": upgrade["feature_code"]
            }
        )
        db.add(purchase)

        await db.commit()
        break

    # Send success message
    upgrade_name = upgrade["name_ru"] if lang == "ru" else upgrade["name_en"]

    if lang == "ru":
        success_text = f"""🎉 <b>Оплата прошла успешно!</b>

Ты разблокировал <b>{upgrade_name}</b>

Теперь твои разговоры станут ещё интереснее и насыщеннее!

Приятного общения! 💜"""
    else:
        success_text = f"""🎉 <b>Payment successful!</b>

You unlocked <b>{upgrade_name}</b>

Now your conversations will be even more interesting and rich!

Enjoy! 💜"""

    await message.answer(success_text, parse_mode="HTML")
    logger.info(f"User {user_id} successfully purchased upgrade {upgrade_id}")
