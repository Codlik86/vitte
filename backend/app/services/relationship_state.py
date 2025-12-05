from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_TRUST = 10
DEFAULT_RESPECT = 0
DEFAULT_CLOSENESS = 5

_TABLE_READY = False


@dataclass
class RelationshipState:
    trust_level: int = DEFAULT_TRUST
    respect_score: int = DEFAULT_RESPECT
    closeness_level: int = DEFAULT_CLOSENESS
    updated_at: datetime | None = None


async def _ensure_table(session: AsyncSession) -> None:
    global _TABLE_READY
    if _TABLE_READY:
        return
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS relationship_states (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                persona_id INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
                trust_level INTEGER NOT NULL DEFAULT :default_trust,
                respect_score INTEGER NOT NULL DEFAULT :default_respect,
                closeness_level INTEGER NOT NULL DEFAULT :default_closeness,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                UNIQUE (user_id, persona_id)
            )
            """
        ),
        {
            "default_trust": DEFAULT_TRUST,
            "default_respect": DEFAULT_RESPECT,
            "default_closeness": DEFAULT_CLOSENESS,
        },
    )
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
            SELECT trust_level, respect_score, closeness_level, updated_at
            FROM relationship_states
            WHERE user_id = :user_id AND persona_id = :persona_id
            """
        ),
        {"user_id": user_id, "persona_id": persona_id},
    )
    row = result.first()
    if row is None:
        return RelationshipState()
    trust_level, respect_score, closeness_level, updated_at = row
    return RelationshipState(
        trust_level=trust_level,
        respect_score=respect_score,
        closeness_level=closeness_level,
        updated_at=updated_at,
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
            INSERT INTO relationship_states (user_id, persona_id, trust_level, respect_score, closeness_level, updated_at)
            VALUES (:user_id, :persona_id, :trust_level, :respect_score, :closeness_level, NOW())
            ON CONFLICT (user_id, persona_id) DO UPDATE
            SET trust_level = EXCLUDED.trust_level,
                respect_score = EXCLUDED.respect_score,
                closeness_level = EXCLUDED.closeness_level,
                updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "persona_id": persona_id,
            "trust_level": state.trust_level,
            "respect_score": state.respect_score,
            "closeness_level": state.closeness_level,
        },
    )
