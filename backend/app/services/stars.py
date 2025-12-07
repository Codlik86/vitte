from __future__ import annotations

from aiogram import Bot
from aiogram.types import LabeledPrice, Message

from .store import get_plan, get_image_pack, get_feature

STARS_CURRENCY = "XTR"


def stars_amount(price_stars: int) -> int:
    return int(price_stars)


async def create_invoice_link(
    bot: Bot,
    *,
    title: str,
    description: str,
    payload: str,
    price_stars: int,
    currency: str = STARS_CURRENCY,
) -> str:
    amount = stars_amount(price_stars)
    prices = [LabeledPrice(label=title, amount=amount)]
    return await bot.create_invoice_link(
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=currency,
        prices=prices,
    )


async def send_stars_invoice_for_subscription(
    bot: Bot,
    recipient: Message | int,
    plan_code: str,
) -> None:
    plan = get_plan(plan_code)
    if plan is None:
        raise ValueError("Plan not found")
    amount = stars_amount(plan.price_stars)
    prices = [LabeledPrice(label=f"Подписка Vitte: {plan.title}", amount=amount)]
    chat_id = recipient.chat.id if isinstance(recipient, Message) else recipient
    await bot.send_invoice(
        chat_id=chat_id,
        title="Подписка Vitte",
        description="Безлимитные сообщения, быстрый режим и премиум-функции.",
        payload=f"sub:{plan_code}",
        provider_token="",
        currency=STARS_CURRENCY,
        prices=prices,
    )


async def send_stars_invoice_for_feature(
    bot: Bot,
    recipient: Message | int,
    feature_code: str,
    title: str,
    description: str,
    price_stars: int | None = None,
    payload_prefix: str = "feat",
) -> None:
    resolved_price = price_stars
    if resolved_price is None and payload_prefix == "feat":
        feat = get_feature(feature_code)
        resolved_price = feat.price_stars if feat else None
    if resolved_price is None and payload_prefix == "pack":
        pack = get_image_pack(feature_code)
        resolved_price = pack.price_stars if pack else None
    if resolved_price is None:
        raise ValueError("Price not found for invoice")

    amount = stars_amount(resolved_price)
    prices = [LabeledPrice(label=title, amount=amount)]
    chat_id = recipient.chat.id if isinstance(recipient, Message) else recipient
    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=f"{payload_prefix}:{feature_code}",
        provider_token="",
        currency=STARS_CURRENCY,
        prices=prices,
    )
