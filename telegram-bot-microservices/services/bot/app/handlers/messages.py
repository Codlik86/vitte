"""
Message handler - process user text messages

Handles incoming text messages from users and sends them to the chat API.
Shows typing indicator and "Печатает..." message while waiting for response.
"""
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatAction
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.api_client import send_chat_message
from shared.database import get_db, Dialog
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="messages")


async def keep_typing(bot: Bot, chat_id: int, interval: float = 4.0):
    """
    Continuously send typing action until cancelled.
    Telegram typing indicator lasts ~5 seconds, so we refresh every 4 seconds.
    """
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        # Task was cancelled - this is expected when API response arrives
        pass


async def get_active_dialog(user_id: int) -> Dialog | None:
    """Get user's most recently updated active dialog"""
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.user_id == user_id, Dialog.is_active == True)
            .order_by(Dialog.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    return None


@router.message(F.text)
async def handle_text_message(message: Message):
    """
    Handle incoming text messages from user.

    Flow:
    1. Check if user has an active dialog
    2. Show typing indicator
    3. Send "Печатает..." placeholder
    4. Call chat API
    5. Edit placeholder with response or send error
    """
    user_id = message.from_user.id
    text = message.text.strip()

    if not text:
        return

    # Skip commands
    if text.startswith("/"):
        return

    # Get active dialog
    dialog = await get_active_dialog(user_id)

    if not dialog:
        # No active dialog - prompt user to start one
        await message.answer(
            "У тебя нет активного диалога. Нажми кнопку ниже, чтобы начать общение.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} sent message without active dialog")
        return

    persona_name = dialog.persona.name if dialog.persona else "Персонаж"

    # Send placeholder message
    placeholder = await message.answer(
        f"<i>{persona_name} печатает...</i>",
        parse_mode="HTML"
    )

    # Start continuous typing indicator (runs until cancelled)
    typing_task = asyncio.create_task(keep_typing(message.bot, user_id))

    try:
        # Call chat API
        result = await send_chat_message(
            telegram_id=user_id,
            message=text,
            persona_id=dialog.persona_id,
            story_id=dialog.story_id,
            atmosphere=dialog.atmosphere,
        )
    finally:
        # Stop typing indicator when API responds (success or error)
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    if result.success and result.response:
        # Edit placeholder with actual response
        try:
            await placeholder.edit_text(
                f"<b>{persona_name}</b>\n\n{result.response}",
                parse_mode="HTML"
            )
        except Exception as e:
            # If edit fails, send as new message
            logger.warning(f"Failed to edit placeholder: {e}")
            await placeholder.delete()
            await message.answer(
                f"<b>{persona_name}</b>\n\n{result.response}",
                parse_mode="HTML"
            )

        logger.info(f"User {user_id} got response from {persona_name} (dialog {result.dialog_id})")

    elif result.is_safety_block:
        await placeholder.edit_text(
            "Не могу ответить на это сообщение. Попробуй написать что-то другое.",
            parse_mode="HTML"
        )
        logger.warning(f"Safety block for user {user_id}")

    else:
        # Error - show error message
        await placeholder.edit_text(
            f"Произошла ошибка. Попробуй еще раз.",
            parse_mode="HTML"
        )
        logger.error(f"Chat error for user {user_id}: {result.error}")
