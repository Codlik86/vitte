import asyncio
from dataclasses import dataclass
from typing import Literal

from aiogram import Bot

from ..logging_config import logger


ChatAction = Literal["typing", "upload_photo"]


@dataclass
class ChatActionHandle:
    stop_event: asyncio.Event
    task: asyncio.Task


async def _run_chat_action(bot: Bot, chat_id: int, action: ChatAction, stop_event: asyncio.Event, interval: float) -> None:
    try:
        while True:
            if stop_event.is_set():
                break
            try:
                await bot.send_chat_action(chat_id, action)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Chat action %s failed for chat %s: %s", action, chat_id, exc)
                break
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
            break
    except asyncio.CancelledError:
        raise


def start_chat_action(bot: Bot, chat_id: int, action: ChatAction, *, interval: float = 4.0) -> ChatActionHandle:
    """
    Starts a background task that keeps sending a chat action until stopped.
    Caller must stop it with stop_chat_action().
    """
    stop_event = asyncio.Event()
    task = asyncio.create_task(_run_chat_action(bot, chat_id, action, stop_event, interval))
    return ChatActionHandle(stop_event=stop_event, task=task)


async def stop_chat_action(handle: ChatActionHandle | None) -> None:
    if handle is None:
        return
    handle.stop_event.set()
    try:
        await asyncio.wait_for(handle.task, timeout=2.0)
    except asyncio.TimeoutError:
        handle.task.cancel()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Chat action task finished with error: %s", exc)
