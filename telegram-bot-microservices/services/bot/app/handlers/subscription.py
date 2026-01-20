"""
Subscription handler - Premium subscription options

Handles subscription button from main menu.
Shows Vitte Premium plans with Telegram Stars pricing.
"""
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from datetime import datetime, timedelta

from shared.database import get_db, User, Subscription, Purchase
from shared.database.services import get_user_by_id
from shared.utils import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
router = Router(name="subscription")


# ==================== SUBSCRIPTION PLANS ====================

SUBSCRIPTION_PLANS = {
    "plus_7d": {
        "name_ru": "Неделя",
        "name_en": "Week",
        "days": 7,
        "price_stars": 150,
        "product_code": "vitte_plus_7d"
    },
    "plus_30d": {
        "name_ru": "Месяц",
        "name_en": "Month",
        "days": 30,
        "price_stars": 450,
        "product_code": "vitte_plus_30d"
    },
    "plus_365d": {
        "name_ru": "Год",
        "name_en": "Year",
        "days": 365,
        "price_stars": 2990,
        "product_code": "vitte_plus_365d"
    }
}


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


PAYMENT_METHOD_RU = """💳 <b>Выбери способ оплаты</b>

Ты выбрал: <b>{plan_name}</b>
Стоимость: <b>{price} ⭐</b>

Как будешь оплачивать?"""

PAYMENT_METHOD_EN = """💳 <b>Choose payment method</b>

You selected: <b>{plan_name}</b>
Price: <b>{price} ⭐</b>

How would you like to pay?"""


# ==================== KEYBOARDS ====================

def get_subscription_keyboard_ru() -> InlineKeyboardMarkup:
    """Subscription plans keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Неделя · 7 дней — 150 ⭐", callback_data="sub:plus_7d"),
        ],
        [
            InlineKeyboardButton(text="Месяц · 30 дней — 450 ⭐", callback_data="sub:plus_30d"),
        ],
        [
            InlineKeyboardButton(text="Год · 365 дней — 2990 ⭐", callback_data="sub:plus_365d"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="sub:back_to_menu"),
        ]
    ])


def get_subscription_keyboard_en() -> InlineKeyboardMarkup:
    """Subscription plans keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Week · 7 days — 150 ⭐", callback_data="sub:plus_7d"),
        ],
        [
            InlineKeyboardButton(text="Month · 30 days — 450 ⭐", callback_data="sub:plus_30d"),
        ],
        [
            InlineKeyboardButton(text="Year · 365 days — 2990 ⭐", callback_data="sub:plus_365d"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="sub:back_to_menu"),
        ]
    ])


def get_payment_method_keyboard_ru(plan_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay:stars:{plan_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="sub:back_to_plans"),
        ]
    ])


def get_payment_method_keyboard_en(plan_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay:stars:{plan_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back to plans", callback_data="sub:back_to_plans"),
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


@router.callback_query(F.data.startswith("sub:plus_"))
async def on_select_plan(callback: CallbackQuery):
    """Handle subscription plan selection - show payment method"""
    await callback.answer()

    # Extract plan_id from callback data (sub:plus_2d -> plus_2d)
    plan_id = callback.data.replace("sub:", "")
    plan = SUBSCRIPTION_PLANS.get(plan_id)

    if not plan:
        await callback.answer("❌ План не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = PAYMENT_METHOD_RU.format(
            plan_name=plan["name_ru"],
            price=plan["price_stars"]
        )
        keyboard = get_payment_method_keyboard_ru(plan_id)
    else:
        text = PAYMENT_METHOD_EN.format(
            plan_name=plan["name_en"],
            price=plan["price_stars"]
        )
        keyboard = get_payment_method_keyboard_en(plan_id)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} selected plan {plan_id}, showing payment methods")


@router.callback_query(F.data == "sub:back_to_plans")
async def on_back_to_plans(callback: CallbackQuery):
    """Handle 'Back to plans' button"""
    await callback.answer()
    await _show_subscription_screen(callback.from_user.id, callback.message.answer)


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


# ==================== PAYMENT HANDLERS ====================

@router.callback_query(F.data.startswith("pay:stars:"))
async def on_pay_with_stars(callback: CallbackQuery, bot: Bot):
    """Handle Telegram Stars payment - send invoice"""
    await callback.answer()

    # Extract plan_id from callback data (pay:stars:plus_2d -> plus_2d)
    plan_id = callback.data.replace("pay:stars:", "")
    plan = SUBSCRIPTION_PLANS.get(plan_id)

    if not plan:
        await callback.answer("❌ План не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # Create invoice
    plan_name = plan["name_ru"] if lang == "ru" else plan["name_en"]

    title = f"💎 {plan_name}"
    description = (
        "Безлимитные сообщения, 20 изображений в день, продвинутые модели ИИ"
        if lang == "ru" else
        "Unlimited messages, 20 images per day, advanced AI models"
    )

    # Create keyboard with Pay button (must be first!) and Main Menu button
    pay_button_text = f"⭐ Оплатить {plan['price_stars']} Stars" if lang == "ru" else f"⭐ Pay {plan['price_stars']} Stars"
    menu_button_text = "🏠 Главное меню" if lang == "ru" else "🏠 Main Menu"

    invoice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_button_text, pay=True)],  # Pay button must be first!
        [InlineKeyboardButton(text=menu_button_text, callback_data="sub:back_to_menu")]
    ])

    # Send invoice
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=f"sub:{plan_id}:{user_id}",
        currency="XTR",  # Telegram Stars currency code
        prices=[LabeledPrice(label=plan_name, amount=plan["price_stars"])],
        reply_markup=invoice_keyboard
    )

    logger.info(f"User {user_id} initiated Stars payment for {plan_id}")


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout query - validate the purchase"""
    # Always accept for now (can add validation logic later)
    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id}")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    """Handle successful payment - activate subscription"""
    payment = message.successful_payment
    user_id = message.from_user.id

    # Parse payload
    payload_parts = payment.invoice_payload.split(":")
    if len(payload_parts) < 2:
        logger.error(f"Invalid payment payload: {payment.invoice_payload}")
        return

    plan_id = payload_parts[1]  # sub:plus_2d:user_id -> plus_2d
    plan = SUBSCRIPTION_PLANS.get(plan_id)

    if not plan:
        logger.error(f"Unknown plan in payment: {plan_id}")
        return

    lang = await get_user_language(user_id)

    # Activate subscription in database
    async for db in get_db():
        # Get or create user
        user = await db.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found for payment")
            return

        # Get or create subscription
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()

        now = datetime.utcnow()
        expires_at = now + timedelta(days=plan["days"])

        if subscription:
            # Extend existing subscription
            if subscription.expires_at and subscription.expires_at > now:
                # Add days to existing expiration
                expires_at = subscription.expires_at + timedelta(days=plan["days"])

            subscription.plan = "premium"
            subscription.is_active = True
            subscription.started_at = now
            subscription.expires_at = expires_at
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan="premium",
                is_active=True,
                started_at=now,
                expires_at=expires_at,
                messages_limit=0,  # Unlimited
                images_limit=20
            )
            db.add(subscription)

        # Update user access status
        user.access_status = "subscription_active"

        # Record purchase
        purchase = Purchase(
            user_id=user_id,
            product_code=plan["product_code"],
            provider="telegram_stars",
            amount=plan["price_stars"],
            currency="XTR",
            status="success",
            meta={
                "telegram_payment_charge_id": payment.telegram_payment_charge_id,
                "provider_payment_charge_id": payment.provider_payment_charge_id,
                "plan_days": plan["days"]
            }
        )
        db.add(purchase)

        await db.commit()
        break

    # Send success message
    plan_name = plan["name_ru"] if lang == "ru" else plan["name_en"]

    if lang == "ru":
        success_text = f"""🎉 <b>Оплата прошла успешно!</b>

Ты активировал <b>{plan_name}</b>

Теперь тебе доступно:
• Безлимитные сообщения
• 20 изображений каждый день
• Продвинутые модели ИИ

Подписка активна до: <b>{expires_at.strftime('%d.%m.%Y')}</b>

Приятного общения! 💜"""
    else:
        success_text = f"""🎉 <b>Payment successful!</b>

You activated <b>{plan_name}</b>

Now you have access to:
• Unlimited messages
• 20 images every day
• Advanced AI models

Subscription active until: <b>{expires_at.strftime('%Y-%m-%d')}</b>

Enjoy! 💜"""

    await message.answer(success_text, parse_mode="HTML")
    logger.info(f"User {user_id} successfully purchased {plan_id}, expires {expires_at}")
