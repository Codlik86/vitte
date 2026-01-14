from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from ..models import FeatureUnlock, User


@dataclass
class FeatureState:
    code: str
    title: str
    description: str
    unlocked: bool
    enabled: bool
    toggleable: bool
    product_code: str
    until: None = None


FEATURE_DEFINITIONS: Dict[str, dict] = {
    "intense_mode": {
        "title": "Режим страсти",
        "description": "Персонаж общается смелее и чувственнее при достаточном доверии.",
        "price_stars": 150,
        "toggleable": True,
    },
    "fantasy_scenes": {
        "title": "Фантазии и сцены",
        "description": "Доступ к особым сценариям и фантазиям.",
        "price_stars": 200,
        "toggleable": True,
    },
}


async def collect_feature_states(session: AsyncSession, user: User) -> Dict[str, FeatureState]:
    result = await session.execute(
        select(FeatureUnlock.feature_code, FeatureUnlock.enabled).where(FeatureUnlock.user_id == user.id)
    )
    rows = result.all()
    unlocked = {row[0] for row in rows}
    enabled_map = {row[0]: row[1] for row in rows}
    states: Dict[str, FeatureState] = {}
    for code, meta in FEATURE_DEFINITIONS.items():
        is_unlocked = code in unlocked
        is_enabled = enabled_map.get(code, False) if is_unlocked else False
        states[code] = FeatureState(
            code=code,
            title=meta["title"],
            description=meta["description"],
            unlocked=is_unlocked,
            enabled=is_enabled,
            toggleable=bool(meta.get("toggleable", True)),
            product_code=code,
        )
    return states


async def unlock_feature(session: AsyncSession, user: User, code: str) -> FeatureUnlock:
    if code not in FEATURE_DEFINITIONS:
        raise ValueError("Unknown feature")
    existing = await session.execute(
        select(FeatureUnlock).where(FeatureUnlock.user_id == user.id, FeatureUnlock.feature_code == code)
    )
    current = existing.scalar_one_or_none()
    if current:
        return current
    unlock = FeatureUnlock(user_id=user.id, feature_code=code)
    session.add(unlock)
    await session.flush()
    return unlock


async def toggle_feature(
    session: AsyncSession,
    user: User,
    feature_code: str,
    enabled: bool,
) -> FeatureState:
    if feature_code not in FEATURE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Feature not found")

    result = await session.execute(
        select(FeatureUnlock).where(
            FeatureUnlock.user_id == user.id,
            FeatureUnlock.feature_code == feature_code,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=400, detail="Feature is not unlocked")

    record.enabled = bool(enabled)
    session.add(record)
    await session.flush()

    states = await collect_feature_states(session, user)
    return states[feature_code]


async def reset_all_feature_unlocks(session: AsyncSession, user: User) -> None:
    await session.execute(delete(FeatureUnlock).where(FeatureUnlock.user_id == user.id))


def build_feature_instruction(states: Dict[str, FeatureState]) -> tuple[str, str | None, int | None]:
    """
    Returns (prompt, mode, max_tokens).
    """
    parts: List[str] = []
    mode: str | None = None
    max_tokens: int | None = None

    if states.get("intense_mode") and states["intense_mode"].unlocked:
        parts.append("Режим страсти активен: персонаж общается смелее и чувственнее.")
    if states.get("fantasy_scenes") and states["fantasy_scenes"].unlocked:
        parts.append("Фантазии и сцены доступны: допускай более образные сценарии, когда это уместно.")

    return (" ".join(parts).strip(), mode, max_tokens)
