import uuid
from typing import Any

from ..config import settings

STARS_PROVIDER_TOKEN = settings.stars_provider_token


def create_stars_invoice(
    user_id: int,
    product_code: str,
    amount_stars: int,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Telegram Stars invoices are issued on the client. Backend simply prepares payload.
    """
    return {
        "invoice_id": f"stars-{uuid.uuid4()}",
        "provider": "stars",
        "amount_stars": amount_stars,
        "description": description,
        "product_code": product_code,
        "metadata": metadata or {},
        "provider_token": STARS_PROVIDER_TOKEN,
        "status": "pending",
        "user_id": user_id,
    }
