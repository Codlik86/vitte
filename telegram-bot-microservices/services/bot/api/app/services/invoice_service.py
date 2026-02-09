"""
Invoice service for creating Telegram Stars and CryptoPay invoices

Uses Telegram Bot API directly (via httpx) to create invoice links
that can be opened in WebApp via Telegram.WebApp.openInvoice()

Also supports CryptoPay (Telegram Crypto Bot) for USDT payments
"""

import httpx
import logging
from typing import Optional

from app.config import config
from shared.services import CryptoPayService

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{config.bot_token}"


async def create_invoice_link(
    title: str,
    description: str,
    payload: str,
    price_stars: int,
    photo_url: Optional[str] = None,
) -> Optional[str]:
    """
    Create Telegram Stars invoice link using Bot API.

    Args:
        title: Product title (1-32 characters)
        description: Product description (1-255 characters)
        payload: Bot-defined invoice payload (1-128 bytes)
        price_stars: Price in Telegram Stars
        photo_url: Optional product photo URL

    Returns:
        Invoice link string or None if failed
    """
    if not config.bot_token:
        logger.error("BOT_TOKEN not configured, cannot create invoice")
        return None

    # Build request payload
    data = {
        "title": title[:32],
        "description": description[:255],
        "payload": payload[:128],
        "currency": "XTR",  # Telegram Stars currency
        "prices": [
            {"label": title[:32], "amount": price_stars}
        ],
    }

    if photo_url:
        data["photo_url"] = photo_url

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/createInvoiceLink",
                json=data,
                timeout=10.0
            )

            result = response.json()

            if result.get("ok"):
                invoice_link = result.get("result")
                logger.info(f"Created invoice link for payload: {payload}")
                return invoice_link
            else:
                logger.error(f"Failed to create invoice: {result.get('description')}")
                return None

    except httpx.RequestError as e:
        logger.error(f"HTTP error creating invoice: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating invoice: {e}")
        return None


# ==================== INVOICE BUILDERS ====================

async def create_subscription_invoice(
    plan_code: str,
    plan_name: str,
    duration_days: int,
    price_stars: int,
    user_id: int,
    lang: str = "ru"
) -> Optional[str]:
    """Create invoice for subscription plan."""
    title = f"Vitte Premium - {plan_name}"

    if lang == "ru":
        description = (
            f"Подписка на {duration_days} дней: безлимитные сообщения, "
            f"20 изображений в день, продвинутые модели ИИ"
        )
    else:
        description = (
            f"{duration_days}-day subscription: unlimited messages, "
            f"20 images per day, advanced AI models"
        )

    payload = f"sub:{plan_code}:{user_id}"

    return await create_invoice_link(
        title=title,
        description=description,
        payload=payload,
        price_stars=price_stars,
    )


async def create_image_pack_invoice(
    pack_code: str,
    images_count: int,
    price_stars: int,
    user_id: int,
    lang: str = "ru"
) -> Optional[str]:
    """Create invoice for image pack."""
    if lang == "ru":
        title = f"{images_count} изображений"
        description = f"Пакет из {images_count} изображений для генерации"
    else:
        title = f"{images_count} images"
        description = f"Pack of {images_count} images for generation"

    payload = f"img:{pack_code}:{user_id}"

    return await create_invoice_link(
        title=title,
        description=description,
        payload=payload,
        price_stars=price_stars,
    )


async def create_feature_invoice(
    feature_code: str,
    feature_title: str,
    feature_description: str,
    price_stars: int,
    user_id: int,
) -> Optional[str]:
    """Create invoice for feature unlock."""
    payload = f"feat:{feature_code}:{user_id}"

    return await create_invoice_link(
        title=feature_title,
        description=feature_description,
        payload=payload,
        price_stars=price_stars,
    )


# ==================== CRYPTOPAY INVOICES ====================

async def create_cryptopay_subscription_invoice(
    plan_code: str,
    plan_name: str,
    duration_days: int,
    price_stars: int,
    user_id: int,
    lang: str = "ru"
) -> Optional[str]:
    """Create CryptoPay invoice for subscription plan."""
    if not config.cryptopay_token:
        logger.error("CRYPTOPAY_TOKEN not configured")
        return None

    cryptopay = CryptoPayService(config.cryptopay_token)

    # Convert Stars to USDT
    price_usdt = CryptoPayService.convert_stars_to_usdt(price_stars)

    title = f"Vitte Premium - {plan_name}"

    if lang == "ru":
        description = (
            f"Подписка на {duration_days} дней: безлимитные сообщения, "
            f"20 изображений в день, продвинутые модели ИИ"
        )
    else:
        description = (
            f"{duration_days}-day subscription: unlimited messages, "
            f"20 images per day, advanced AI models"
        )

    payload = f"sub:{plan_code}:{user_id}"

    invoice_data = await cryptopay.create_invoice(
        amount=price_usdt,
        asset="USDT",
        description=f"{title} - {description}",
        payload=payload,
    )

    if invoice_data:
        return CryptoPayService.get_pay_url(invoice_data)
    return None


async def create_cryptopay_image_pack_invoice(
    pack_code: str,
    images_count: int,
    price_stars: int,
    user_id: int,
    lang: str = "ru"
) -> Optional[str]:
    """Create CryptoPay invoice for image pack."""
    if not config.cryptopay_token:
        logger.error("CRYPTOPAY_TOKEN not configured")
        return None

    cryptopay = CryptoPayService(config.cryptopay_token)

    # Convert Stars to USDT
    price_usdt = CryptoPayService.convert_stars_to_usdt(price_stars)

    if lang == "ru":
        title = f"{images_count} изображений"
        description = f"Пакет из {images_count} изображений для генерации"
    else:
        title = f"{images_count} images"
        description = f"Pack of {images_count} images for generation"

    payload = f"images:{pack_code}:{user_id}"

    invoice_data = await cryptopay.create_invoice(
        amount=price_usdt,
        asset="USDT",
        description=f"{title} - {description}",
        payload=payload,
    )

    if invoice_data:
        return CryptoPayService.get_pay_url(invoice_data)
    return None


async def create_cryptopay_feature_invoice(
    feature_code: str,
    feature_title: str,
    feature_description: str,
    price_stars: int,
    user_id: int,
) -> Optional[str]:
    """Create CryptoPay invoice for feature unlock."""
    if not config.cryptopay_token:
        logger.error("CRYPTOPAY_TOKEN not configured")
        return None

    cryptopay = CryptoPayService(config.cryptopay_token)

    # Convert Stars to USDT
    price_usdt = CryptoPayService.convert_stars_to_usdt(price_stars)

    payload = f"upgrade:{feature_code}:{user_id}"

    invoice_data = await cryptopay.create_invoice(
        amount=price_usdt,
        asset="USDT",
        description=f"{feature_title} - {feature_description}",
        payload=payload,
    )

    if invoice_data:
        return CryptoPayService.get_pay_url(invoice_data)
    return None
