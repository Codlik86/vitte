import math
import os

from aiogram import Bot
from aiogram.types import LabeledPrice, Message

STARS_CURRENCY = "XTR"

# Подбираем коэффициент, чтобы покрывать комиссию Telegram и маржу
STARS_RUB_MULTIPLIER = float(os.getenv("STARS_RUB_MULTIPLIER", "1.3"))
STARS_ROUND_STEP = int(os.getenv("STARS_ROUND_STEP", "10"))


def rub_to_stars(price_rub: int) -> int:
    raw = price_rub * STARS_RUB_MULTIPLIER
    if STARS_ROUND_STEP > 1:
        return int(math.ceil(raw / STARS_ROUND_STEP) * STARS_ROUND_STEP)
    return int(math.ceil(raw))


async def send_stars_invoice_for_subscription(
    bot: Bot,
    recipient: Message | int,
    plan_code: str,
    price_rub: int,
) -> None:
    amount_stars = rub_to_stars(price_rub)
    prices = [LabeledPrice(label=f"Подписка Vitte: {plan_code}", amount=amount_stars)]
    chat_id = recipient.chat.id if isinstance(recipient, Message) else recipient

    await bot.send_invoice(
        chat_id=chat_id,
        title="Подписка Vitte",
        description="Безлимитные сообщения, быстрый режим и премиум-функции.",
        payload=f"sub:{plan_code}",
        provider_token="",  # для Stars не нужен токен
        currency=STARS_CURRENCY,
        prices=prices,
    )


async def send_stars_invoice_for_feature(
    bot: Bot,
    recipient: Message | int,
    feature_code: str,
    title: str,
    description: str,
    price_rub: int,
) -> None:
    amount_stars = rub_to_stars(price_rub)
    prices = [LabeledPrice(label=title, amount=amount_stars)]
    chat_id = recipient.chat.id if isinstance(recipient, Message) else recipient

    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=f"feat:{feature_code}",
        provider_token="",  # для Stars не нужен токен
        currency=STARS_CURRENCY,
        prices=prices,
    )
