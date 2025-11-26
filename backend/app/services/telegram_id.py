from __future__ import annotations

import os
from typing import Optional

from fastapi import Request, HTTPException, status

from ..logging_config import logger
from .telegram_webapp import extract_telegram_user_from_request

TELEGRAM_DEBUG_ID_ENV_KEYS = [
    "VITTE_DEBUG_TELEGRAM_ID",
    "VITTE_DEBUG_ID",
    "vite_debug_id",
    "VITE_DEBUG_TELEGRAM_ID",
]


def get_debug_telegram_id() -> Optional[int]:
    for key in TELEGRAM_DEBUG_ID_ENV_KEYS:
        value = os.getenv(key)
        if value:
            try:
                return int(value)
            except ValueError:
                continue
    return None


async def extract_telegram_id_from_request(request: Request) -> Optional[int]:
    """
    Пытается достать telegram_id из запроса:
    - query-параметры: telegram_id, telegramId
    - заголовки: X-Telegram-Id, X-Telegram-User-Id
    - тело JSON: telegram_id / telegramId
    """
    candidates = []

    qp = request.query_params
    for key in ("telegram_id", "telegramId"):
        if qp.get(key):
            candidates.append(qp.get(key))

    headers = request.headers
    for key in ("x-telegram-id", "x-telegram-user-id"):
        if headers.get(key):
            candidates.append(headers.get(key))

    # Попробуем достать из JSON-тела, если оно есть
    try:
        body = await request.json()
        if isinstance(body, dict):
            for key in ("telegram_id", "telegramId"):
                if body.get(key) is not None:
                    candidates.append(body.get(key))
    except Exception:
        # тело не JSON или не читается — игнорируем
        pass

    for raw in candidates:
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


async def get_or_raise_telegram_id(
    request: Request,
    *,
    explicit: int | None = None,
    allow_debug: bool = True,
    allow_telegram_id_param: bool = True,
) -> int:
    env = (os.getenv("ENV") or "").lower()
    is_prod = env == "prod"
    if explicit:
        return int(explicit)

    # Пытаемся достать из WebApp initData (с валидацией) или других источников
    user = await extract_telegram_user_from_request(
        request,
        allow_debug=allow_debug,
        allow_telegram_id_param=allow_telegram_id_param,
    )
    real_id = user.id if user else None

    if real_id:
        return real_id

    # Фоллбек на старую схему (заголовки/квери), если WebApp недоступен
    if not is_prod:
        real_id = await extract_telegram_id_from_request(request)
        if real_id:
            return real_id

    if allow_debug:
        debug_id = get_debug_telegram_id()
        env_flag = (os.getenv("ENV") or "").lower()
        debug_flag = os.getenv("VITTE_DEBUG_MODE") == "1" or env_flag in {"dev", "local", "development"}
        if debug_id and debug_flag:
            return debug_id

    logger.warning("Failed to resolve telegram id")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="не удалось определить telegram id",
    )
