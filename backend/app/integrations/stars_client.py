from ..config import settings

# Здесь позже будет логика Telegram Stars
STARS_PROVIDER_TOKEN = settings.stars_provider_token


def create_fake_stars_invoice(user_id: int) -> dict:
    """
    Заглушка для покупки через Telegram Stars.
    """
    return {
        "user_id": user_id,
        "status": "pending",
        "provider": "stars",
    }
