"""
Shop handler - Image packs store

Handles shop button from main menu.
Shows available image packs with Telegram Stars pricing.
"""
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from datetime import datetime

from shared.database import get_db, User, ImageBalance, Purchase
from shared.database.services import get_user_by_id, get_subscription_by_user_id
from shared.utils import get_logger
from shared.services import CryptoPayService
from sqlalchemy import select
from app.config import config

logger = get_logger(__name__)
router = Router(name="shop")


# ==================== IMAGE PACKS ====================

IMAGE_PACKS = {
    "pack_20": {
        "name_ru": "20 изображений",
        "name_en": "20 images",
        "images": 20,
        "price_stars": 50,
        "product_code": "images_pack_20"
    },
    "pack_50": {
        "name_ru": "50 изображений",
        "name_en": "50 images",
        "images": 50,
        "price_stars": 120,
        "product_code": "images_pack_50"
    },
    "pack_100": {
        "name_ru": "100 изображений",
        "name_en": "100 images",
        "images": 100,
        "price_stars": 250,
        "product_code": "images_pack_100"
    },
    "pack_200": {
        "name_ru": "200 изображений",
        "name_en": "200 images",
        "images": 200,
        "price_stars": 500,
        "product_code": "images_pack_200"
    }
}


# ==================== TEXTS ====================

# Shop hub screen
SHOP_HUB_RU = """🛒 <b>Магазин</b>

Здесь можно докупить изображения.

Выбери раздел:"""

SHOP_HUB_EN = """🛒 <b>Shop</b>

Here you can buy more images.

Choose a section:"""

# Images section
SHOP_IMAGES_RU = """🖼 <b>Магазин изображений</b>

У тебя <b>{images_count}</b> изображений.

Докупи ещё — выбери нужный пакет:"""

SHOP_IMAGES_EN = """🖼 <b>Image Shop</b>

You have <b>{images_count}</b> images.

Buy more — choose a pack:"""


PAYMENT_METHOD_RU = """💳 <b>Выбери способ оплаты</b>

Ты выбрал: <b>{pack_name}</b>
Стоимость: <b>{price} ⭐</b>

Как будешь оплачивать?"""

PAYMENT_METHOD_EN = """💳 <b>Choose payment method</b>

You selected: <b>{pack_name}</b>
Price: <b>{price} ⭐</b>

How would you like to pay?"""


# ==================== KEYBOARDS ====================

def get_shop_hub_keyboard_ru() -> InlineKeyboardMarkup:
    """Shop hub keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼 Купить изображения", callback_data="shop:images"),
        ],
        # [
        #     InlineKeyboardButton(text="✨ Купить улучшения", callback_data="shop:upgrades"),
        # ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="shop:back_to_menu"),
        ]
    ])


def get_shop_hub_keyboard_en() -> InlineKeyboardMarkup:
    """Shop hub keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼 Buy Images", callback_data="shop:images"),
        ],
        # [
        #     InlineKeyboardButton(text="✨ Buy Upgrades", callback_data="shop:upgrades"),
        # ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="shop:back_to_menu"),
        ]
    ])


def get_images_keyboard_ru() -> InlineKeyboardMarkup:
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
            InlineKeyboardButton(text="⭐ Купить Stars по СБП", url="https://t.me/tribute/app?startapp=plsg"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="shop:back_to_hub"),
        ]
    ])


def get_images_keyboard_en() -> InlineKeyboardMarkup:
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
            InlineKeyboardButton(text="⭐ Buy Stars", url="https://t.me/tribute/app?startapp=plsg"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="shop:back_to_hub"),
        ]
    ])


def get_payment_method_keyboard_ru(pack_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (Russian)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"shop_pay:stars:{pack_id}"),
        ],
        [
            InlineKeyboardButton(text="₮ CryptoPay USDT", callback_data=f"shop_pay:crypto:{pack_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к пакетам", callback_data="shop:images"),
        ]
    ])


def get_payment_method_keyboard_en(pack_id: str) -> InlineKeyboardMarkup:
    """Payment method selection keyboard (English)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"shop_pay:stars:{pack_id}"),
        ],
        [
            InlineKeyboardButton(text="₮ CryptoPay USDT", callback_data=f"shop_pay:crypto:{pack_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Back to packs", callback_data="shop:images"),
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
        # Check image balance
        result = await db.execute(
            select(ImageBalance).where(ImageBalance.user_id == user_id)
        )
        image_balance = result.scalar_one_or_none()
        if image_balance:
            return image_balance.remaining_purchased_images or 0
    return 0


# ==================== HANDLERS ====================

async def _show_shop_hub(user_id: int, target):
    """Show shop hub screen with categories"""
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = SHOP_HUB_RU
        keyboard = get_shop_hub_keyboard_ru()
    else:
        text = SHOP_HUB_EN
        keyboard = get_shop_hub_keyboard_en()

    # Send shop hub with photo
    await target.answer_photo(
        photo=config.shop_image_url,
        caption=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"User {user_id} opened shop hub")


async def _show_images_screen(user_id: int, respond_func):
    """Show images shop screen"""
    lang = await get_user_language(user_id)
    images_count = await get_user_images_count(user_id)

    if lang == "ru":
        text = SHOP_IMAGES_RU.format(images_count=images_count)
        keyboard = get_images_keyboard_ru()
    else:
        text = SHOP_IMAGES_EN.format(images_count=images_count)
        keyboard = get_images_keyboard_en()

    await respond_func(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} opened images shop, balance: {images_count}")


@router.message(Command("shop"))
async def cmd_shop(message: Message):
    """Handle /shop command"""
    await _show_shop_hub(message.from_user.id, message)


@router.callback_query(F.data == "menu:shop")
async def on_shop(callback: CallbackQuery):
    """Handle 'Shop' button from main menu"""
    await callback.answer()
    await _show_shop_hub(callback.from_user.id, callback.message)


@router.callback_query(F.data == "shop:images")
async def on_shop_images(callback: CallbackQuery):
    """Handle 'Buy Images' button from shop hub"""
    await callback.answer()
    await _show_images_screen(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data == "shop:upgrades")
async def on_shop_upgrades(callback: CallbackQuery):
    """Handle 'Buy Upgrades' button from shop hub - redirect to upgrades"""
    await callback.answer()

    # Import and show upgrades screen
    from app.handlers.upgrades import _show_upgrades_screen
    await _show_upgrades_screen(callback.from_user.id, callback.message.answer)


@router.callback_query(F.data == "shop:back_to_hub")
async def on_back_to_hub(callback: CallbackQuery):
    """Handle 'Back' button - return to shop hub"""
    await callback.answer()

    # If message has photo, delete it and send new message
    if callback.message and callback.message.photo:
        await callback.message.delete()
        await _show_shop_hub(callback.from_user.id, callback.message.bot)
    else:
        await _show_shop_hub(callback.from_user.id, callback.message)


@router.callback_query(F.data.startswith("shop:pack_"))
async def on_select_pack(callback: CallbackQuery):
    """Handle image pack selection - show payment method"""
    await callback.answer()

    # Extract pack_id from callback data (shop:pack_20 -> pack_20)
    pack_id = callback.data.replace("shop:", "")
    pack = IMAGE_PACKS.get(pack_id)

    if not pack:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = PAYMENT_METHOD_RU.format(
            pack_name=pack["name_ru"],
            price=pack["price_stars"]
        )
        keyboard = get_payment_method_keyboard_ru(pack_id)
    else:
        text = PAYMENT_METHOD_EN.format(
            pack_name=pack["name_en"],
            price=pack["price_stars"]
        )
        keyboard = get_payment_method_keyboard_en(pack_id)

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} selected pack {pack_id}, showing payment methods")


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


# ==================== PAYMENT HANDLERS ====================

@router.callback_query(F.data.startswith("shop_pay:stars:"))
async def on_pay_with_stars(callback: CallbackQuery, bot: Bot):
    """Handle Telegram Stars payment - send invoice"""
    await callback.answer()

    # Extract pack_id from callback data (shop_pay:stars:pack_20 -> pack_20)
    pack_id = callback.data.replace("shop_pay:stars:", "")
    pack = IMAGE_PACKS.get(pack_id)

    if not pack:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    # Create invoice
    pack_name = pack["name_ru"] if lang == "ru" else pack["name_en"]

    title = f"🖼 {pack_name}"
    description = (
        f"Пакет из {pack['images']} изображений для генерации"
        if lang == "ru" else
        f"Pack of {pack['images']} images for generation"
    )

    # Create keyboard with Pay button (must be first!) and Main Menu button
    pay_button_text = f"⭐ Оплатить {pack['price_stars']} Stars" if lang == "ru" else f"⭐ Pay {pack['price_stars']} Stars"
    menu_button_text = "🏠 Главное меню" if lang == "ru" else "🏠 Main Menu"

    invoice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_button_text, pay=True)],  # Pay button must be first!
        [InlineKeyboardButton(text=menu_button_text, callback_data="shop:back_to_menu")]
    ])

    # Send invoice
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=f"images:{pack_id}:{user_id}",
        currency="XTR",  # Telegram Stars currency code
        prices=[LabeledPrice(label=pack_name, amount=pack["price_stars"])],
        reply_markup=invoice_keyboard
    )

    logger.info(f"User {user_id} initiated Stars payment for {pack_id}")


@router.callback_query(F.data.startswith("shop_pay:crypto:"))
async def on_pay_with_crypto(callback: CallbackQuery, bot: Bot):
    """Handle CryptoPay USDT payment - send payment link"""
    await callback.answer()

    # Extract pack_id from callback data (shop_pay:crypto:pack_20 -> pack_20)
    pack_id = callback.data.replace("shop_pay:crypto:", "")
    pack = IMAGE_PACKS.get(pack_id)

    if not pack:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if not config.cryptopay_token:
        error_text = "❌ CryptoPay временно недоступен" if lang == "ru" else "❌ CryptoPay temporarily unavailable"
        await callback.message.answer(error_text)
        return

    cryptopay = CryptoPayService(config.cryptopay_token)

    # Convert Stars to USDT
    price_usdt = CryptoPayService.convert_stars_to_usdt(pack["price_stars"])

    # Create CryptoPay invoice
    pack_name = pack["name_ru"] if lang == "ru" else pack["name_en"]

    description = (
        f"Пакет из {pack['images']} изображений для генерации"
        if lang == "ru" else
        f"Pack of {pack['images']} images for generation"
    )

    payload = f"images:{pack_id}:{user_id}"

    invoice_data = await cryptopay.create_invoice(
        amount=price_usdt,
        asset="USDT",
        description=description,
        payload=payload,
    )

    if not invoice_data:
        error_text = "❌ Не удалось создать счёт. Попробуйте позже." if lang == "ru" else "❌ Failed to create invoice. Try again later."
        await callback.message.answer(error_text)
        return

    pay_url = CryptoPayService.get_pay_url(invoice_data)

    if not pay_url:
        error_text = "❌ Ошибка получения ссылки на оплату" if lang == "ru" else "❌ Failed to get payment link"
        await callback.message.answer(error_text)
        return

    # Send payment link
    pay_text = (
        f"💳 <b>Оплата через CryptoPay</b>\n\n"
        f"Пакет: <b>{pack_name}</b>\n"
        f"Сумма: <b>{price_usdt} USDT</b>\n\n"
        f"Нажми на кнопку ниже для оплаты:"
        if lang == "ru" else
        f"💳 <b>Payment via CryptoPay</b>\n\n"
        f"Pack: <b>{pack_name}</b>\n"
        f"Amount: <b>{price_usdt} USDT</b>\n\n"
        f"Click the button below to pay:"
    )

    pay_button_text = "💳 Оплатить USDT" if lang == "ru" else "💳 Pay USDT"
    menu_button_text = "🏠 Главное меню" if lang == "ru" else "🏠 Main Menu"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_button_text, url=pay_url)],
        [InlineKeyboardButton(text=menu_button_text, callback_data="shop:back_to_menu")]
    ])

    await callback.message.answer(pay_text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"User {user_id} initiated CryptoPay payment for {pack_id} ({price_usdt} USDT)")


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout query - validate the purchase"""
    # Check if this is an images purchase
    if not pre_checkout_query.invoice_payload.startswith("images:"):
        return  # Let other handlers process it

    # Always accept for now (can add validation logic later)
    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id} (images)")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    """Handle successful payment - add images to balance"""
    payment = message.successful_payment
    user_id = message.from_user.id

    # Check if this is an images purchase
    if not payment.invoice_payload.startswith("images:"):
        return  # Let other handlers process it

    # Parse payload
    payload_parts = payment.invoice_payload.split(":")
    if len(payload_parts) < 2:
        logger.error(f"Invalid payment payload: {payment.invoice_payload}")
        return

    pack_id = payload_parts[1]  # images:pack_20:user_id -> pack_20
    pack = IMAGE_PACKS.get(pack_id)

    if not pack:
        logger.error(f"Unknown pack in payment: {pack_id}")
        return

    lang = await get_user_language(user_id)

    # Add images to balance in database
    async for db in get_db():
        # Get or create user
        user = await db.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found for payment")
            return

        # Get or create image balance
        result = await db.execute(
            select(ImageBalance).where(ImageBalance.user_id == user_id)
        )
        image_balance = result.scalar_one_or_none()

        if image_balance:
            # Add to existing balance
            image_balance.total_purchased_images += pack["images"]
            image_balance.remaining_purchased_images += pack["images"]
        else:
            # Create new image balance
            image_balance = ImageBalance(
                user_id=user_id,
                total_purchased_images=pack["images"],
                remaining_purchased_images=pack["images"]
            )
            db.add(image_balance)

        # Record purchase
        purchase = Purchase(
            user_id=user_id,
            product_code=pack["product_code"],
            provider="telegram_stars",
            amount=pack["price_stars"],
            currency="XTR",
            status="success",
            meta={
                "telegram_payment_charge_id": payment.telegram_payment_charge_id,
                "provider_payment_charge_id": payment.provider_payment_charge_id,
                "images_count": pack["images"]
            }
        )
        db.add(purchase)

        await db.commit()

        new_balance = image_balance.remaining_purchased_images
        break

    # Send success message
    pack_name = pack["name_ru"] if lang == "ru" else pack["name_en"]

    if lang == "ru":
        success_text = f"""🎉 <b>Оплата прошла успешно!</b>

Ты купил <b>{pack_name}</b>

Теперь у тебя <b>{new_balance}</b> изображений для генерации.

Приятного использования! 💜"""
    else:
        success_text = f"""🎉 <b>Payment successful!</b>

You purchased <b>{pack_name}</b>

Now you have <b>{new_balance}</b> images for generation.

Enjoy! 💜"""

    await message.answer(success_text, parse_mode="HTML")
    logger.info(f"User {user_id} successfully purchased {pack_id}, new balance: {new_balance}")
