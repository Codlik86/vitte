from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional
from urllib.parse import parse_qsl

from pydantic import BaseModel

from ..config import settings
from ..logging_config import logger


class TelegramWebAppUser(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


def _get_debug_telegram_id() -> Optional[int]:
    debug_keys = [
        "VITTE_DEBUG_TELEGRAM_ID",
        "VITTE_DEBUG_ID",
        "vite_debug_id",
        "VITE_DEBUG_TELEGRAM_ID",
    ]
    for key in debug_keys:
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError:
                continue
    return None


def _parse_init_data(init_data: str, bot_token: str) -> dict:
    if not init_data:
        raise ValueError("Init data is empty")
    parsed_pairs = parse_qsl(init_data, keep_blank_values=True)
    data = {k: v for k, v in parsed_pairs}
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("Hash is missing in init data")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash != received_hash:
        raise ValueError("Invalid init data signature")

    return data


def extract_telegram_user(
    init_data: Optional[str],
    telegram_id_param: Optional[str] = None,
    allow_debug: bool = False,
) -> TelegramWebAppUser:
    """
    1) В prod: парсим init_data и валидируем подпись, возвращаем user.id, иначе ValueError.
    2) В dev: допускаем VITE_DEBUG_TELEGRAM_ID (если allow_debug) и telegram_id_param как fallback.
    """
    env = (os.getenv("ENV") or "").lower()
    is_prod = env == "prod"

    # В проде работаем только с валидным init_data
    if init_data:
        data = _parse_init_data(init_data, settings.telegram_bot_token)
        user_raw = data.get("user")
        if not user_raw:
            raise ValueError("User not found in init data")
        try:
            import json

            parsed_user = json.loads(user_raw)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Failed to parse user payload") from exc
        try:
            return TelegramWebAppUser.model_validate(parsed_user)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid user payload") from exc

    if is_prod:
        raise ValueError("Init data is required in production")

    # Dev-only фоллбеки
    if allow_debug:
        debug_id = _get_debug_telegram_id()
        if debug_id:
            return TelegramWebAppUser(id=debug_id)

    if telegram_id_param:
        try:
            return TelegramWebAppUser(id=int(telegram_id_param))
        except (TypeError, ValueError):
            pass

    raise ValueError("Failed to extract telegram user")


async def extract_telegram_user_from_request(
    request,
    *,
    allow_debug: bool = False,
    allow_telegram_id_param: bool = True,
) -> TelegramWebAppUser | None:
    """
    Пытается достать пользователя из:
    - заголовков: X-Telegram-Web-App-Init-Data / X-Telegram-WebApp-Data
    - query/body поля init_data
    - dev-фоллбеков при allow_debug=True
    """
    headers = request.headers
    init_data = (
        headers.get("x-telegram-web-app-init-data")
        or headers.get("x-telegram-webapp-init-data")
        or headers.get("x-telegram-web-app-data")
        or headers.get("x-telegram-webapp-data")
    )

    if not init_data:
        qp = request.query_params
        init_data = qp.get("init_data") or qp.get("initData")

    if not init_data:
        try:
            body = await request.json()
            if isinstance(body, dict):
                init_data = body.get("init_data") or body.get("initData")
        except Exception:  # noqa: BLE001
            init_data = None

    telegram_id_param = None
    if allow_telegram_id_param:
        telegram_id_param = (
            request.query_params.get("telegram_id")
            or request.query_params.get("telegramId")
        )
        if not telegram_id_param:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    telegram_id_param = body.get("telegram_id") or body.get("telegramId")
            except Exception:  # noqa: BLE001
                telegram_id_param = None

    try:
        return extract_telegram_user(init_data, telegram_id_param, allow_debug=allow_debug)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to extract telegram user: %s", exc)
        return None
