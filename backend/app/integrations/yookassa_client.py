from typing import Any

from yookassa import Configuration

from ..config import settings

if settings.yookassa_shop_id and settings.yookassa_secret_key:
    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key

# Здесь позже появятся функции create_payment, capture_payment и т.д.


def create_fake_subscription_payment(user_id: int) -> dict[str, Any]:
    """
    Заглушка. Позже будет реальный платёж в YooKassa.
    Сейчас просто возвращаем фиктивные данные.
    """
    return {
        "user_id": user_id,
        "status": "pending",
        "provider": "yookassa",
    }
