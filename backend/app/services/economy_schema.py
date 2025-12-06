from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


DDL_CREATE_IMAGE_BALANCES = """
CREATE TABLE IF NOT EXISTS image_balances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    total_purchased_images INTEGER NOT NULL DEFAULT 0,
    remaining_purchased_images INTEGER NOT NULL DEFAULT 0,
    daily_subscription_quota INTEGER NOT NULL DEFAULT 20,
    daily_subscription_used INTEGER NOT NULL DEFAULT 0,
    daily_quota_date TIMESTAMP WITHOUT TIME ZONE NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
"""

DDL_CREATE_FEATURE_UNLOCKS = """
CREATE TABLE IF NOT EXISTS feature_unlocks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feature_code VARCHAR(64) NOT NULL,
    unlocked_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (user_id, feature_code)
);
"""

DDA_ALTER_FEATURE_UNLOCKS_ENABLED = """
ALTER TABLE feature_unlocks
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;
"""

DDL_DROP_LEGACY_USER_FEATURE_COLUMNS = """
ALTER TABLE users
    DROP COLUMN IF EXISTS feature_long_letters_until,
    DROP COLUMN IF EXISTS feature_long_letters_enabled,
    DROP COLUMN IF EXISTS feature_voice_until,
    DROP COLUMN IF EXISTS feature_voice_enabled,
    DROP COLUMN IF EXISTS feature_deep_mode_until,
    DROP COLUMN IF EXISTS feature_deep_mode_enabled,
    DROP COLUMN IF EXISTS feature_images_until;
"""


async def ensure_economy_schema(session: AsyncSession) -> None:
    try:
        await session.execute(text(DDL_CREATE_IMAGE_BALANCES))
        await session.execute(text(DDL_CREATE_FEATURE_UNLOCKS))
        await session.execute(text(DDA_ALTER_FEATURE_UNLOCKS_ENABLED))
        await session.execute(text(DDL_DROP_LEGACY_USER_FEATURE_COLUMNS))
    except Exception:  # noqa: BLE001
        logger.exception("Failed to ensure economy schema (image balances, feature unlocks, legacy cleanup)")
        raise
