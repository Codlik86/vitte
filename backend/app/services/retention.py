from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..bot import bot
from ..db import async_session_factory
from ..logging_config import logger
from ..models import Dialog, Message, Persona, User
from .analytics import log_event

FOLLOWUP_DELAY = timedelta(minutes=3)
REMINDER_DELAYS = [
    (timedelta(hours=1), "remind_1h_sent", "retention_remind_1h"),
    (timedelta(days=1), "remind_1d_sent", "retention_remind_1d"),
    (timedelta(days=7), "remind_7d_sent", "retention_remind_7d"),
]
SURPRISE_DELAY = timedelta(days=3)


async def start_retention_worker() -> asyncio.Task:
    return asyncio.create_task(_retention_loop(), name="retention-loop")


async def _retention_loop():
    while True:
        try:
            async with async_session_factory() as session:
                await process_followups(session)
                await process_reminders(session)
                await process_surprises(session)
                await session.commit()
        except Exception as exc:
            logger.error("Retention loop error: %s", exc)
        await asyncio.sleep(60)


async def process_followups(session: AsyncSession):
    now = datetime.utcnow()
    dialogs_result = await session.execute(
        select(Dialog).order_by(Dialog.created_at.desc()).limit(50)
    )
    dialogs: Iterable[Dialog] = dialogs_result.scalars().all()
    for dialog in dialogs:
        messages_result = await session.execute(
            select(Message)
            .where(Message.dialog_id == dialog.id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        messages = list(messages_result.scalars().all())
        last_assistant = next((m for m in messages if m.role == "assistant"), None)
        last_user = next((m for m in messages if m.role == "user"), None)
        if not last_assistant:
            continue
        if last_user and last_user.created_at > last_assistant.created_at:
            continue
        if dialog.last_followup_sent_at and dialog.last_followup_sent_at >= last_assistant.created_at:
            continue
        age = now - last_assistant.created_at
        if age < timedelta(minutes=2) or age > timedelta(minutes=6):
            continue
        text = "Я всё ещё здесь и думаю о тебе. Как ты сейчас?"  # short and safe
        await _send_retention_message(session, dialog, text)
        dialog.last_followup_sent_at = now
        await log_event(session, dialog.user_id, "retention_fup_sent", {"dialog_id": dialog.id})


async def process_reminders(session: AsyncSession):
    now = datetime.utcnow()
    dialogs_result = await session.execute(
        select(Dialog).order_by(Dialog.created_at.desc()).limit(100)
    )
    dialogs: Iterable[Dialog] = dialogs_result.scalars().all()
    for dialog in dialogs:
        last_message_time = await _last_message_time(session, dialog.id)
        if not last_message_time:
            continue
        for delay, flag_name, event_name in REMINDER_DELAYS:
            already_sent = getattr(dialog, flag_name, False)
            if already_sent:
                continue
            if now - last_message_time >= delay:
                text = "Я скучаю по тебе. Когда вернёшься, расскажи, что новенького?"
                await _send_retention_message(session, dialog, text)
                setattr(dialog, flag_name, True)
                dialog.last_reminder_sent_at = now
                await log_event(session, dialog.user_id, event_name, {"dialog_id": dialog.id})


async def process_surprises(session: AsyncSession):
    now = datetime.utcnow()
    users_result = await session.execute(select(User))
    users: Iterable[User] = users_result.scalars().all()
    for user in users:
        last_sent = user.last_surprise_sent_at
        if last_sent and now - last_sent < SURPRISE_DELAY:
            continue
        dialog_result = await session.execute(
            select(Dialog).where(Dialog.user_id == user.id).order_by(Dialog.created_at.desc()).limit(1)
        )
        dialog = dialog_result.scalar_one_or_none()
        if not dialog:
            continue
        last_message_time = await _last_message_time(session, dialog.id)
        if not last_message_time or now - last_message_time > timedelta(days=14):
            continue
        text = "У меня есть маленький комплимент для тебя: ты делаешь наш чат особенным. Напишешь пару строк?"
        await _send_retention_message(session, dialog, text)
        user.last_surprise_sent_at = now
        await log_event(session, user.id, "mini_surprise_sent", {"dialog_id": dialog.id})


async def _last_message_time(session: AsyncSession, dialog_id: int) -> datetime | None:
    result = await session.execute(
        select(Message).where(Message.dialog_id == dialog_id).order_by(Message.created_at.desc()).limit(1)
    )
    last_message = result.scalar_one_or_none()
    return last_message.created_at if last_message else None


async def _send_retention_message(session: AsyncSession, dialog: Dialog, text: str):
    user = await session.get(User, dialog.user_id)
    persona = await session.get(Persona, dialog.character_id) if dialog.character_id else None
    if not user or not user.telegram_id:
        return
    prefix = f"{persona.name}: " if persona else ""
    try:
        await bot.send_message(user.telegram_id, f"{prefix}{text}")
    except Exception as exc:
        logger.error("Failed to send retention message: %s", exc)
