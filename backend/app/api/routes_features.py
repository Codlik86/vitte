from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Dialog, Message, User
from ..schemas import (
    FeatureStatusResponse,
    FeatureToggleRequest,
    FeatureToggleResponse,
    SimpleOkResponse,
)
from ..services.analytics import log_event
from ..services.features import collect_feature_states, toggle_feature
from ..users_service import get_or_create_user_by_telegram_id
from ..services.telegram_id import get_or_raise_telegram_id

router = APIRouter(prefix="/api/features", tags=["features"])


def _serialize_features(states):
    return [
        {
            "code": feature.code,
            "title": feature.title,
            "description": feature.description,
            "active": feature.unlocked and feature.enabled,
            "enabled": feature.enabled,
            "until": feature.until,
            "product_code": feature.product_code,
            "toggleable": feature.toggleable,
        }
        for feature in states.values()
    ]


@router.get("/status", response_model=FeatureStatusResponse)
async def feature_status(
    request: Request,
    telegram_id: int | None = Query(default=None, description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    states = await collect_feature_states(session, user)
    await session.commit()
    return {"features": _serialize_features(states)}


@router.post("/toggle", response_model=FeatureToggleResponse)
async def feature_toggle(
    payload: FeatureToggleRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=payload.telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    state = await toggle_feature(session, user, payload.feature_code, payload.enabled)
    await log_event(
        session,
        user.id,
        "feature_toggled",
        {"feature_code": payload.feature_code, "enabled": payload.enabled},
    )
    await session.commit()
    return {
        "feature": {
            "code": state.code,
            "title": state.title,
            "description": state.description,
            "active": state.active,
            "enabled": state.enabled,
            "until": state.until,
            "product_code": state.product_code,
            "toggleable": state.toggleable,
        },
        "ok": True,
    }


@router.post("/clear-dialogs", response_model=SimpleOkResponse)
async def clear_dialogs(
    request: Request,
    telegram_id: int | None = Query(default=None, description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    dialog_ids_result = await session.execute(select(Dialog.id).where(Dialog.user_id == user.id))
    dialog_ids = [row[0] for row in dialog_ids_result.all()]
    if dialog_ids:
        await session.execute(delete(Message).where(Message.dialog_id.in_(dialog_ids)))
        for dialog_id in dialog_ids:
            dialog = await session.get(Dialog, dialog_id)
            if dialog:
                dialog.last_followup_sent_at = None
                dialog.remind_1h_sent = False
                dialog.remind_1d_sent = False
                dialog.remind_7d_sent = False
                dialog.last_reminder_sent_at = None
    await log_event(session, user.id, "dialogs_cleared", {"dialog_ids": dialog_ids})
    await session.commit()
    return SimpleOkResponse()


@router.post("/clear-long-memory", response_model=SimpleOkResponse)
async def clear_long_memory(
    request: Request,
    telegram_id: int | None = Query(default=None, description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    user = await get_or_create_user_by_telegram_id(session, telegram_id)
    await log_event(session, user.id, "long_memory_cleared", {})
    await session.commit()
    return SimpleOkResponse()


@router.post("/delete-account", response_model=SimpleOkResponse)
async def delete_account(
    request: Request,
    telegram_id: int | None = Query(default=None, description="Telegram user id"),
    session: AsyncSession = Depends(get_session),
):
    telegram_id = await get_or_raise_telegram_id(request, explicit=telegram_id)
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        await session.delete(user)
        await log_event(session, user.id, "account_deleted", {})
        await session.commit()
    return SimpleOkResponse()
