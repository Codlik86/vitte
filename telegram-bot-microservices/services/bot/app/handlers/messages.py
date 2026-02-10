"""
Message handler - process user text messages

Handles incoming text messages from users and sends them to the chat API.
Shows typing indicator and "Печатает..." message while waiting for response.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.api_client import send_chat_message
from shared.database import get_db, Dialog, User, Subscription
from shared.database.services import get_user_by_id
from shared.utils import get_logger
from shared.utils.redis import redis_client

logger = get_logger(__name__)
router = Router(name="messages")


# ==================== TEXTS ====================

NO_DIALOG_RU = "У тебя нет активного диалога. Нажми кнопку ниже, чтобы начать общение."
NO_DIALOG_EN = "You don't have an active dialog. Click the button below to start chatting."

LIMIT_REACHED_RU = """⏸ <b>Дневной лимит исчерпан</b>

Ты использовал все {limit} бесплатных сообщений на сегодня.

Чтобы продолжить общение — оформи подписку 💎"""

LIMIT_REACHED_EN = """⏸ <b>Daily limit reached</b>

You've used all {limit} free messages for today.

To continue chatting — get a subscription 💎"""

TYPING_RU = "{name} печатает..."
TYPING_EN = "{name} is typing..."

SAFETY_BLOCK_RU = "Не могу ответить на это сообщение. Попробуй написать что-то другое."
SAFETY_BLOCK_EN = "I can't respond to that message. Try writing something else."

ERROR_RU = "Произошла ошибка. Попробуй еще раз."
ERROR_EN = "An error occurred. Please try again."

USER_NOT_FOUND_RU = "Пользователь не найден"
USER_NOT_FOUND_EN = "User not found"

LIMIT_CHECK_ERROR_RU = "Ошибка проверки лимита"
LIMIT_CHECK_ERROR_EN = "Error checking limit"


# ==================== HELPER FUNCTIONS ====================

async def get_user_language(user_id: int) -> str:
    """Get user language from DB, default to 'ru'"""
    async for db in get_db():
        user = await get_user_by_id(db, user_id)
        if user:
            if isinstance(user, dict):
                return user.get("language_code", "ru")
            else:
                return user.language_code or "ru"
    return "ru"


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


async def check_message_limit(user_id: int, lang: str) -> tuple[bool, str | None]:
    """
    Check if user can send a message (free users have 20 messages/day limit).
    Uses Redis for fast counter with automatic daily reset.
    Returns (can_send, error_message)
    """
    # Check subscription status from DB (cached by get_user_by_id)
    async for db in get_db():
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()

        # If subscription is active, no limit
        if subscription and subscription.is_active:
            now = datetime.now(timezone.utc)
            if subscription.expires_at and subscription.expires_at > now:
                return True, None
        break

    # Free user - check daily limit via Redis
    redis_key = f"user:{user_id}:messages:daily"

    try:
        # Get current count from Redis
        current_count = await redis_client.get(redis_key)

        if current_count is None:
            # First message today - set counter to 1 with TTL until midnight
            now = datetime.now(timezone.utc)
            # Calculate seconds until midnight UTC
            midnight = datetime(now.year, now.month, now.day, 23, 59, 59)
            seconds_until_midnight = int((midnight - now).total_seconds()) + 1

            await redis_client.set(redis_key, "1", expire=seconds_until_midnight)
            return True, None

        count = int(current_count)

        # Check if limit exceeded (20 messages/day)
        if count >= 20:
            error_template = LIMIT_REACHED_RU if lang == "ru" else LIMIT_REACHED_EN
            error = error_template.format(limit=20)
            return False, error

        # Increment counter atomically
        await redis_client.increment(redis_key)
        return True, None

    except Exception as e:
        logger.error(f"Redis error checking message limit for user {user_id}: {e}")
        # Fallback - allow message on Redis error
        return True, None


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

    # Get user language
    lang = await get_user_language(user_id)

    # Get active dialog
    dialog = await get_active_dialog(user_id)

    if not dialog:
        # No active dialog - prompt user to start one
        no_dialog_text = NO_DIALOG_RU if lang == "ru" else NO_DIALOG_EN
        await message.answer(no_dialog_text, parse_mode="HTML")
        logger.info(f"User {user_id} sent message without active dialog")
        return

    # Check message limit for free users
    can_send, error_msg = await check_message_limit(user_id, lang)
    if not can_send:
        # Show limit reached message with subscription and menu buttons
        if lang == "ru":
            sub_button_text = "💎 Подписка"
            menu_button_text = "🏠 Главное меню"
        else:
            sub_button_text = "💎 Subscription"
            menu_button_text = "🏠 Main Menu"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=sub_button_text, callback_data="menu:subscription")],
            [InlineKeyboardButton(text=menu_button_text, callback_data="menu:back_to_menu")]
        ])
        await message.answer(error_msg, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"User {user_id} reached daily message limit")
        return

    persona_name = dialog.persona.name if dialog.persona else ("Персонаж" if lang == "ru" else "Character")

    # Send placeholder message
    typing_text = TYPING_RU if lang == "ru" else TYPING_EN
    placeholder = await message.answer(
        f"<i>{typing_text.format(name=persona_name)}</i>",
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
        # Create inline keyboard with refresh button
        refresh_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄", callback_data=f"refresh:{result.dialog_id}:{placeholder.message_id}")
        ]])

        # Save context for refresh in Redis (TTL: 1 hour)
        try:
            refresh_context_key = f"refresh:{result.dialog_id}:{placeholder.message_id}"
            await redis_client.set(
                refresh_context_key,
                text,  # user's original message
                expire=3600  # 1 hour
            )
        except Exception as e:
            logger.warning(f"Failed to save refresh context: {e}")

        # Check if image was generated
        if result.image_url:
            import httpx
            from aiogram.types import BufferedInputFile

            # Download image from MinIO BEFORE deleting placeholder
            photo_file = None
            try:
                internal_url = result.image_url.replace(
                    "https://craveme.tech/storage/", "http://minio:9000/vitte-bot/"
                )
                async with httpx.AsyncClient() as http_client:
                    img_resp = await http_client.get(internal_url, timeout=10.0)
                    if img_resp.status_code == 200:
                        photo_file = BufferedInputFile(img_resp.content, filename="photo.png")
                    else:
                        logger.error(f"Failed to download image: HTTP {img_resp.status_code} from {internal_url}")
            except Exception as e:
                logger.error(f"Failed to download photo: {e}")

            # Delete placeholder, then send photo + text back-to-back
            try:
                await placeholder.delete()
            except Exception:
                pass

            if photo_file:
                for attempt in range(3):
                    try:
                        await message.answer_photo(photo=photo_file)
                        break
                    except Exception as e:
                        logger.error(f"Failed to send photo (attempt {attempt+1}/3): {e}")
                        if attempt < 2:
                            await asyncio.sleep(2)

            try:
                await message.answer(
                    f"<b>{persona_name}</b>\n\n{result.response}",
                    parse_mode="HTML",
                    reply_markup=refresh_keyboard
                )
                logger.info(f"User {user_id} got image + response from {persona_name} (dialog {result.dialog_id})")
            except Exception as e:
                logger.error(f"Failed to send text after photo: {e}")
        else:
            # No image - edit placeholder with text response + refresh button
            try:
                await placeholder.edit_text(
                    f"<b>{persona_name}</b>\n\n{result.response}",
                    parse_mode="HTML",
                    reply_markup=refresh_keyboard
                )
            except Exception as e:
                # If edit fails, send as new message
                logger.warning(f"Failed to edit placeholder: {e}")
                await placeholder.delete()
                await message.answer(
                    f"<b>{persona_name}</b>\n\n{result.response}",
                    parse_mode="HTML",
                    reply_markup=refresh_keyboard
                )

            logger.info(f"User {user_id} got response from {persona_name} (dialog {result.dialog_id})")

    elif result.is_safety_block:
        safety_text = SAFETY_BLOCK_RU if lang == "ru" else SAFETY_BLOCK_EN
        await placeholder.edit_text(safety_text, parse_mode="HTML")
        logger.warning(f"Safety block for user {user_id}")

    else:
        # Error - show error message
        error_text = ERROR_RU if lang == "ru" else ERROR_EN
        await placeholder.edit_text(error_text, parse_mode="HTML")
        logger.error(f"Chat error for user {user_id}: {result.error}")


@router.callback_query(F.data.startswith("refresh:"))
async def handle_refresh(callback: CallbackQuery):
    """
    Handle refresh button - regenerate LLM response with same context.

    Callback data format: refresh:{dialog_id}:{message_id}
    """
    await callback.answer()
    user_id = callback.from_user.id

    # Parse callback data
    try:
        _, dialog_id_str, message_id_str = callback.data.split(":")
        dialog_id = int(dialog_id_str)
        message_id = int(message_id_str)
    except (ValueError, IndexError):
        logger.error(f"Invalid refresh callback data: {callback.data}")
        return

    # Get user language
    lang = await get_user_language(user_id)

    # Get user message from Redis
    refresh_context_key = f"refresh:{dialog_id}:{message_id}"
    try:
        user_message = await redis_client.get(refresh_context_key)
        if not user_message:
            error_text = "Не могу обновить - контекст устарел" if lang == "ru" else "Cannot refresh - context expired"
            await callback.answer(error_text, show_alert=True)
            logger.warning(f"Refresh context expired for dialog {dialog_id}, message {message_id}")
            return
    except Exception as e:
        logger.error(f"Redis error getting refresh context: {e}")
        error_text = "Ошибка обновления" if lang == "ru" else "Refresh error"
        await callback.answer(error_text, show_alert=True)
        return

    # Get dialog with persona
    async for db in get_db():
        result_query = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.id == dialog_id, Dialog.user_id == user_id)
        )
        dialog = result_query.scalar_one_or_none()

        if not dialog:
            await callback.answer("Диалог не найден" if lang == "ru" else "Dialog not found", show_alert=True)
            return

        persona_name = dialog.persona.name if dialog.persona else ("Персонаж" if lang == "ru" else "Character")
        break

    # Update message to show "regenerating..." state
    typing_text = TYPING_RU if lang == "ru" else TYPING_EN
    try:
        await callback.message.edit_text(
            f"<i>{typing_text.format(name=persona_name)}</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Failed to edit message during refresh: {e}")

    # Start continuous typing indicator
    typing_task = asyncio.create_task(keep_typing(callback.bot, user_id))

    try:
        # Call chat API with same user message (will generate NEW response)
        result = await send_chat_message(
            telegram_id=user_id,
            message=user_message,
            persona_id=dialog.persona_id,
            story_id=dialog.story_id,
            atmosphere=dialog.atmosphere,
        )
    finally:
        # Stop typing indicator
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    if result.success and result.response:
        # Create inline keyboard with refresh button (same format)
        refresh_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄", callback_data=f"refresh:{result.dialog_id}:{callback.message.message_id}")
        ]])

        # Update message with new response
        try:
            await callback.message.edit_text(
                f"<b>{persona_name}</b>\n\n{result.response}",
                parse_mode="HTML",
                reply_markup=refresh_keyboard
            )
        except Exception as e:
            logger.warning(f"Failed to edit message with refreshed response: {e}")

        logger.info(f"User {user_id} refreshed response for dialog {dialog_id}")

    else:
        # Error
        error_text = ERROR_RU if lang == "ru" else ERROR_EN
        try:
            await callback.message.edit_text(error_text, parse_mode="HTML")
        except Exception:
            pass
        logger.error(f"Refresh error for user {user_id}: {result.error}")
