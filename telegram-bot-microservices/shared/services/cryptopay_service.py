"""
CryptoPay Integration Service
Handles invoice creation and webhook processing for CryptoPay (Telegram Crypto Bot)
"""

import hashlib
import hmac
import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CryptoPayService:
    """Service for CryptoPay API interactions"""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": api_token}

    async def create_invoice(
        self,
        amount: float,
        currency_type: str = "crypto",
        asset: str = "USDT",
        description: str = "",
        payload: str = "",
        expires_in: int = 3600,  # 1 hour
    ) -> Optional[Dict[str, Any]]:
        """
        Create CryptoPay invoice via POST request.

        Returns:
            Invoice data dict with pay_url/mini_app_url or None on error
        """
        url = f"{self.base_url}/createInvoice"

        body = {
            "amount": str(amount),
            "currency_type": currency_type,
            "asset": asset,
            "description": description[:1024],
            "payload": payload,
            "expires_in": expires_in,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=body) as resp:
                    if resp.status != 200:
                        logger.error(f"CryptoPay API error: {resp.status} - {await resp.text()}")
                        return None

                    data = await resp.json()

                    if not data.get("ok"):
                        logger.error(f"CryptoPay API returned error: {data}")
                        return None

                    result = data.get("result", {})
                    logger.info(f"Created CryptoPay invoice: {result.get('invoice_id')}, pay_url: {result.get('pay_url') or result.get('mini_app_url')}")
                    return result

        except Exception as e:
            logger.error(f"Failed to create CryptoPay invoice: {e}", exc_info=True)
            return None

    async def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        url = f"{self.base_url}/getInvoices"
        params = {"invoice_ids": str(invoice_id)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"CryptoPay API error: {resp.status}")
                        return None

                    data = await resp.json()

                    if not data.get("ok"):
                        return None

                    items = data.get("result", {}).get("items", [])
                    return items[0] if items else None

        except Exception as e:
            logger.error(f"Failed to get CryptoPay invoice: {e}", exc_info=True)
            return None

    def verify_webhook_signature(self, body_raw: bytes, signature: str) -> bool:
        """
        Verify CryptoPay webhook signature using HMAC-SHA-256.

        The secret key is SHA-256 hash of the app's API token.
        The signature is HMAC-SHA-256 of the raw request body.
        Header: crypto-pay-api-signature
        """
        try:
            # Secret = SHA256(api_token)
            secret = hashlib.sha256(self.api_token.encode()).digest()

            # Expected = HMAC-SHA256(secret, body)
            expected_signature = hmac.new(secret, body_raw, hashlib.sha256).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def parse_webhook_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse webhook update from CryptoPay.

        Format:
        {
            "update_id": 123456,
            "update_type": "invoice_paid",
            "request_date": "2024-01-15T12:00:00Z",
            "payload": {  // Invoice object
                "invoice_id": 12345,
                "status": "paid",
                "amount": "10.00",
                "asset": "USDT",
                "payload": "sub:plus_30d:12345",
                ...
            }
        }
        """
        try:
            update_type = update_data.get("update_type")

            if update_type != "invoice_paid":
                logger.info(f"Ignoring CryptoPay update type: {update_type}")
                return None

            invoice = update_data.get("payload", {})
            status = invoice.get("status")

            if status != "paid":
                logger.info(f"Invoice not paid yet: {status}")
                return None

            return {
                "invoice_id": invoice.get("invoice_id"),
                "amount": float(invoice.get("amount", 0)),
                "asset": invoice.get("asset"),
                "payload": invoice.get("payload", ""),
                "paid_at": invoice.get("paid_at"),
                "paid_amount": float(invoice.get("paid_amount", 0) or 0),
                "paid_asset": invoice.get("paid_asset"),
                "tx_id": invoice.get("hash"),
            }

        except Exception as e:
            logger.error(f"Failed to parse CryptoPay webhook: {e}", exc_info=True)
            return None

    @staticmethod
    def get_pay_url(invoice_data: Dict[str, Any]) -> Optional[str]:
        """Extract payment URL from invoice data (pay_url or mini_app_url)"""
        return invoice_data.get("pay_url") or invoice_data.get("mini_app_url")

    @staticmethod
    def convert_stars_to_usdt(stars: int, star_price_usdt: float = 0.013) -> float:
        """
        Convert Telegram Stars to USDT.

        Current rate: ~$0.013 per star (approximate).

        Returns:
            Amount in USDT (rounded to 2 decimals)
        """
        usdt_amount = stars * star_price_usdt
        return round(usdt_amount, 2)
