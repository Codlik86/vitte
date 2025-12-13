from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import async_session_factory
from ..logging_config import logger
from ..models import Dialog, EventAnalytics, Message, Persona, User
from .analytics import log_event

# Time windows to avoid pinging stale chats
MAX_FOLLOWUP_AGE_HOURS = 24
MAX_REMINDER_AGE_DAYS = 7
MAX_SURPRISE_AGE_DAYS = 14

# Delivery cadence
FOLLOWUP_WINDOW = (timedelta(minutes=3), timedelta(minutes=10))
REMINDER_DELAYS = [
    (timedelta(hours=1), "remind_1h_sent", "retention_remind_1h"),
    (timedelta(days=1), "remind_1d_sent", "retention_remind_1d"),
    (timedelta(days=7), "remind_7d_sent", "retention_remind_7d"),
]
SURPRISE_DELAY = timedelta(days=3)
DAILY_RETENTION_LIMIT = 1
RETENTION_EVENT_TYPES = {
    "retention_fup_sent",
    "retention_remind_1h",
    "retention_remind_1d",
    "retention_remind_7d",
    "mini_surprise_sent",
}


@dataclass
class DialogSnapshot:
    dialog: Dialog
    last_assistant_message: Message | None
    last_user_message: Message | None
    last_message_at: datetime | None


async def start_retention_worker() -> asyncio.Task:
    return asyncio.create_task(_retention_loop(), name="retention-loop")


def retention_status() -> str:
    # Simple helper for health check; relies on task name search
    for task in asyncio.all_tasks():
        if task.get_name() == "retention-loop":
            return "running" if not task.cancelled() else "stopped"
    return "stopped"


async def _retention_loop():
    while True:
        try:
            async with async_session_factory() as session:
                await process_retention(session)
                await session.commit()
        except Exception as exc:
            logger.error("Retention loop error: %s", exc)
        await asyncio.sleep(60)


async def process_retention(session: AsyncSession):
    now = datetime.utcnow()
    users_result = await session.execute(select(User))
    users: Iterable[User] = users_result.scalars().all()

    for user in users:
        try:
            sent = await _process_user_retention(session, user, now)
            if sent:
                continue
        except Exception as exc:  # noqa: PERF203 - keep isolation per user
            logger.error("Retention user %s error: %s", user.id, exc)


async def _process_user_retention(session: AsyncSession, user: User, now: datetime) -> bool:
    if await _is_rate_limited(session, user.id, now):
        return False

    snapshot = await _latest_dialog_snapshot(session, user.id)
    if not snapshot or not snapshot.last_message_at:
        return False

    last_message_age = now - snapshot.last_message_at
    if last_message_age > timedelta(days=MAX_SURPRISE_AGE_DAYS):
        return False

    # Priority ladder: follow-up -> 1h -> 1d -> 7d -> surprise
    if await _try_followup(session, snapshot, now):
        return True

    if await _try_reminders(session, snapshot, now):
        return True

    if await _try_surprise(session, user, snapshot, now):
        return True

    return False


async def _send_retention_message(session: AsyncSession, dialog: Dialog, text: str):
    user = await session.get(User, dialog.user_id)
    persona = await session.get(Persona, dialog.character_id) if dialog.character_id else None
    if not user or not user.telegram_id:
        return
    prefix = f"{persona.name}: " if persona else ""
    logger.info("Retention message to %s skipped (bot not available): %s%s", user.telegram_id, prefix, text)


async def _latest_dialog_snapshot(session: AsyncSession, user_id: int) -> DialogSnapshot | None:
    last_message_dialog_result = await session.execute(
        select(Message.dialog_id)
        .join(Dialog, Dialog.id == Message.dialog_id)
        .where(Dialog.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    dialog_id = last_message_dialog_result.scalar_one_or_none()

    if dialog_id is None:
        dialog_fallback = await session.execute(
            select(Dialog.id).where(Dialog.user_id == user_id).order_by(Dialog.created_at.desc()).limit(1)
        )
        dialog_id = dialog_fallback.scalar_one_or_none()

    if dialog_id is None:
        return None

    dialog = await session.get(Dialog, dialog_id)
    if not dialog:
        return None

    messages_result = await session.execute(
        select(Message)
        .where(Message.dialog_id == dialog_id)
        .order_by(Message.created_at.desc())
        .limit(5)
    )
    messages = list(messages_result.scalars().all())
    last_assistant = next((m for m in messages if m.role == "assistant"), None)
    last_user = next((m for m in messages if m.role == "user"), None)
    last_message_at = messages[0].created_at if messages else None

    return DialogSnapshot(
        dialog=dialog,
        last_assistant_message=last_assistant,
        last_user_message=last_user,
        last_message_at=last_message_at,
    )


async def _is_rate_limited(session: AsyncSession, user_id: int, now: datetime) -> bool:
    window_start = now - timedelta(hours=24)
    result = await session.execute(
        select(func.count(EventAnalytics.id)).where(
            and_(
                EventAnalytics.user_id == user_id,
                EventAnalytics.created_at >= window_start,
                EventAnalytics.event_type.in_(RETENTION_EVENT_TYPES),
            )
        )
    )
    count = result.scalar_one() or 0
    return count >= DAILY_RETENTION_LIMIT


async def _try_followup(session: AsyncSession, snapshot: DialogSnapshot, now: datetime) -> bool:
    dialog = snapshot.dialog
    last_assistant = snapshot.last_assistant_message
    last_user = snapshot.last_user_message

    if not last_assistant:
        return False

    if last_user and last_user.created_at > last_assistant.created_at:
        return False

    if dialog.last_followup_sent_at and dialog.last_followup_sent_at >= last_assistant.created_at:
        return False

    age = now - last_assistant.created_at
    if not (FOLLOWUP_WINDOW[0] <= age <= FOLLOWUP_WINDOW[1]):
        return False

    if age > timedelta(hours=MAX_FOLLOWUP_AGE_HOURS):
        return False

    text = "Я всё ещё здесь и думаю о тебе. Как ты сейчас?"
    await _send_retention_message(session, dialog, text)
    dialog.last_followup_sent_at = now
    await log_event(session, dialog.user_id, "retention_fup_sent", {"dialog_id": dialog.id})
    logger.info("Retention followup sent user=%s dialog=%s", dialog.user_id, dialog.id)
    return True


async def _try_reminders(session: AsyncSession, snapshot: DialogSnapshot, now: datetime) -> bool:
    dialog = snapshot.dialog
    last_assistant = snapshot.last_assistant_message
    last_user = snapshot.last_user_message
    last_message_at = snapshot.last_message_at

    if not last_message_at:
        return False

    # Only remind if assistant spoke last and user did not respond
    if not last_assistant or (last_user and last_user.created_at > last_assistant.created_at):
        return False

    last_message_age = now - last_message_at
    for delay, flag_name, event_name in REMINDER_DELAYS:
        already_sent = getattr(dialog, flag_name, False)
        if already_sent:
            continue

        if delay >= timedelta(days=7) and last_message_age > timedelta(days=MAX_REMINDER_AGE_DAYS):
            continue

        if delay < timedelta(days=7) and last_message_age > timedelta(hours=MAX_FOLLOWUP_AGE_HOURS):
            continue

        if last_message_age >= delay:
            text = "Я скучаю по тебе. Когда вернёшься, расскажи, что новенького?"
            await _send_retention_message(session, dialog, text)
            setattr(dialog, flag_name, True)
            dialog.last_reminder_sent_at = now
            await log_event(session, dialog.user_id, event_name, {"dialog_id": dialog.id})
            logger.info("Retention reminder %s sent user=%s dialog=%s", event_name, dialog.user_id, dialog.id)
            return True

    return False


async def _try_surprise(session: AsyncSession, user: User, snapshot: DialogSnapshot, now: datetime) -> bool:
    last_message_at = snapshot.last_message_at
    if not last_message_at:
        return False

    if user.last_surprise_sent_at and now - user.last_surprise_sent_at < SURPRISE_DELAY:
        return False

    if now - last_message_at > timedelta(days=MAX_SURPRISE_AGE_DAYS):
        return False

    text = "У меня есть маленький комплимент для тебя: ты делаешь наш чат особенным. Напишешь пару строк?"
    await _send_retention_message(session, snapshot.dialog, text)
    user.last_surprise_sent_at = now
    snapshot.dialog.last_reminder_sent_at = now
    await log_event(session, user.id, "mini_surprise_sent", {"dialog_id": snapshot.dialog.id})
    logger.info("Retention surprise sent user=%s dialog=%s", user.id, snapshot.dialog.id)
    return True
