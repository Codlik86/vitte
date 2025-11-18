from yookassa import Configuration

from ..config import settings

if settings.yookassa_shop_id and settings.yookassa_secret_key:
    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key

# Здесь позже появятся функции create_payment, capture_payment и т.д.
