from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from enum import IntEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings

DEFAULT_TRUST = 10
DEFAULT_RESPECT = 0
DEFAULT_CLOSENESS = 5

_TABLE_READY = False
logger = logging.getLogger(__name__)


class RelationshipLevel(IntEnum):
    INIT = 0
    FRIENDLY = 1
    ROMANTIC = 2


@dataclass
class RelationshipState:
    trust_level: int = DEFAULT_TRUST
    respect_score: int = DEFAULT_RESPECT
    closeness_level: int = DEFAULT_CLOSENESS
    updated_at: datetime | None = None
    relationship_level: RelationshipLevel | None = None
    manual_override: bool = False


def apply_test_mode(state: "RelationshipState", enabled: bool) -> "RelationshipState":
    if not enabled:
        return state
    return RelationshipState(
        trust_level=0,
        respect_score=0,
        closeness_level=0,
        updated_at=state.updated_at,
        relationship_level=state.relationship_level,
        manual_override=state.manual_override,
    )


def level_to_state(level: RelationshipLevel) -> RelationshipState:
    if level == RelationshipLevel.ROMANTIC:
        return RelationshipState(trust_level=85, respect_score=0, closeness_level=80)
    if level == RelationshipLevel.FRIENDLY:
        return RelationshipState(trust_level=50, respect_score=0, closeness_level=50)
    return RelationshipState(trust_level=DEFAULT_TRUST, respect_score=DEFAULT_RESPECT, closeness_level=DEFAULT_CLOSENESS)


def derive_level_from_state(state: RelationshipState) -> RelationshipLevel:
    if state.relationship_level is not None:
        try:
            return RelationshipLevel(state.relationship_level)
        except ValueError:
            pass
    if state.trust_level >= 70 or state.closeness_level >= 70:
        return RelationshipLevel.ROMANTIC
    if state.trust_level >= 30 or state.closeness_level >= 30:
        return RelationshipLevel.FRIENDLY
    return RelationshipLevel.INIT


def describe_level(level: RelationshipLevel) -> str:
    if level == RelationshipLevel.ROMANTIC:
        return "Романтика и флирт разрешены, действуй смело но бережно."
    if level == RelationshipLevel.FRIENDLY:
        return "Открытый тёплый диалог, без лишних отказов, держи комфорт и уважение."
    return "Мягкий прогрев и лёгкий флирт, без откровенности."


def transition_level(
    current_level: RelationshipLevel,
    *,
    message_count: int,
    analysis,
) -> RelationshipLevel:
    level = current_level
    if message_count >= 20:
        level = max(level, RelationshipLevel.FRIENDLY)
    if analysis and (analysis.is_flirty or analysis.is_romantic or analysis.asks_for_intimacy):
        if not analysis.is_rude and not analysis.is_pushy:
            level = RelationshipLevel.ROMANTIC
    if analysis and (analysis.is_rude or analysis.is_pushy):
        level = min(level, RelationshipLevel.FRIENDLY)
    return level


async def _ensure_table(session: AsyncSession) -> None:
    global _TABLE_READY
    if _TABLE_READY:
        return
    try:
        await session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS relationship_states (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    persona_id INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
                    trust_level INTEGER NOT NULL DEFAULT 10,
                    respect_score INTEGER NOT NULL DEFAULT 0,
                    closeness_level INTEGER NOT NULL DEFAULT 5,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    relationship_level SMALLINT NOT NULL DEFAULT 0,
                    manual_override BOOLEAN NOT NULL DEFAULT FALSE,
                    UNIQUE (user_id, persona_id)
                )
                """
            )
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to ensure relationship_states table exists")
        raise
        await session.execute(
            text("ALTER TABLE relationship_states ADD COLUMN IF NOT EXISTS relationship_level SMALLINT DEFAULT 0")
        )
        await session.execute(
            text("ALTER TABLE relationship_states ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT FALSE")
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to ensure relationship_states table exists")
        raise
    _TABLE_READY = True


def _clamp(value: int, min_v: int, max_v: int) -> int:
    return max(min_v, min(max_v, value))


def describe_relationship(state: RelationshipState) -> str:
    trust_text = "только знакомитесь"
    if state.trust_level >= 40:
        trust_text = "давно и близко общаетесь"
    elif state.trust_level >= 15:
        trust_text = "уже неплохо общаетесь"

    respect_text = "обычно уважителен"
    if state.respect_score < -3:
        respect_text = "часто грубит или давит"
    elif state.respect_score > 3:
        respect_text = "очень уважителен и заботлив"

    closeness_text = "пока дружески и аккуратно"
    if state.closeness_level >= 40:
        closeness_text = "очень близкие отношения, допустим флирт и интим"
    elif state.closeness_level >= 15:
        closeness_text = "ощутимый флирт и вовлечённость"

    return (
        f"Доверие: {state.trust_level} ({trust_text}). "
        f"Уважение: {state.respect_score} ({respect_text}). "
        f"Близость: {state.closeness_level} ({closeness_text})."
    )


def choose_relationship_mode(state: RelationshipState) -> str:
    if state.respect_score < -3:
        return "hurt"
    if state.trust_level > 40 and state.closeness_level > 50 and state.respect_score >= 0:
        return "very_close"
    if state.trust_level > 15 and state.closeness_level > 20 and state.respect_score >= -2:
        return "friendly"
    return "getting_to_know"


def update_relationship_state(
    state: RelationshipState,
    *,
    trust_delta: int = 0,
    respect_delta: int = 0,
    closeness_delta: int = 0,
) -> RelationshipState:
    trust = _clamp(state.trust_level + trust_delta, 0, 100)
    respect = _clamp(state.respect_score + respect_delta, -10, 10)
    closeness = _clamp(state.closeness_level + closeness_delta, 0, 100)
    return RelationshipState(
        trust_level=trust,
        respect_score=respect,
        closeness_level=closeness,
        updated_at=state.updated_at,
    )


async def get_relationship_state(session: AsyncSession, user_id: int, persona_id: int) -> RelationshipState:
    await _ensure_table(session)
    result = await session.execute(
        text(
            """
            SELECT trust_level, respect_score, closeness_level, updated_at, relationship_level, manual_override
            FROM relationship_states
            WHERE user_id = :user_id AND persona_id = :persona_id
            """
        ),
        {"user_id": user_id, "persona_id": persona_id},
    )
    row = result.first()
    if row is None:
        return RelationshipState()
    # Handle legacy rows without new columns
    if len(row) >= 6:
        trust_level, respect_score, closeness_level, updated_at, relationship_level, manual_override = row
    else:
        trust_level, respect_score, closeness_level, updated_at = row
        relationship_level = None
        manual_override = False
    return RelationshipState(
        trust_level=trust_level,
        respect_score=respect_score,
        closeness_level=closeness_level,
        updated_at=updated_at,
        relationship_level=relationship_level if relationship_level is not None else None,
        manual_override=bool(manual_override),
    )


async def save_relationship_state(
    session: AsyncSession,
    user_id: int,
    persona_id: int,
    state: RelationshipState,
) -> None:
    await _ensure_table(session)
    await session.execute(
        text(
            """
            INSERT INTO relationship_states (
                user_id, persona_id, trust_level, respect_score, closeness_level, relationship_level, manual_override, updated_at
            )
            VALUES (:user_id, :persona_id, :trust_level, :respect_score, :closeness_level, :relationship_level, :manual_override, NOW())
            ON CONFLICT (user_id, persona_id) DO UPDATE
            SET trust_level = EXCLUDED.trust_level,
                respect_score = EXCLUDED.respect_score,
                closeness_level = EXCLUDED.closeness_level,
                relationship_level = EXCLUDED.relationship_level,
                manual_override = EXCLUDED.manual_override,
                updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "persona_id": persona_id,
            "trust_level": state.trust_level,
            "respect_score": state.respect_score,
            "closeness_level": state.closeness_level,
            "relationship_level": int(state.relationship_level or derive_level_from_state(state)),
            "manual_override": bool(state.manual_override),
        },
    )
