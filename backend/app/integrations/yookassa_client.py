from typing import Any

import hmac
import hashlib
import uuid

import httpx

from ..config import settings

API_URL = "https://api.yookassa.ru/v3/payments"


async def create_payment(
    amount: int,
    currency: str,
    description: str,
    return_url: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Creates a payment in YooKassa. Falls back to a fake payload if credentials are missing.
    """
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        return {
            "id": f"fake-{uuid.uuid4()}",
            "status": "pending",
            "amount": {"value": amount, "currency": currency},
            "confirmation": {
                "type": "redirect",
                "confirmation_url": return_url,
            },
            "metadata": metadata,
        }

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": currency},
        "description": description,
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
        },
        "metadata": metadata,
    }

    headers = {"Idempotence-Key": str(uuid.uuid4())}
    auth = httpx.BasicAuth(settings.yookassa_shop_id, settings.yookassa_secret_key)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(API_URL, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        return response.json()


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    """
    YooKassa webhooks contain an HMAC SHA-256 signature in the Content-HMAC header.
    """
    if not settings.yookassa_secret_key:
        return True
    if not signature:
        return False
    expected = hmac.new(settings.yookassa_secret_key.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
