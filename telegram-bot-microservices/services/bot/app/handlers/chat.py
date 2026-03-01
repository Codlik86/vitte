"""
Chat handler - Start Chat button logic

Handles "Начать общение" button from main menu.
Shows active dialogs list or prompts to create new.
"""
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx

from app.config import config
from shared.database import get_db, Dialog, Subscription
from shared.database.services import get_user_by_id
from shared.utils import get_logger
from shared.utils.redis import redis_client
from shared.llm.personas import PERSONAS
from app.handlers.messages import PERSONA_KEY_TO_EN_NAME

logger = get_logger(__name__)
router = Router(name="chat")


# ==================== TEXTS ====================

# Has active dialogs
HAS_DIALOGS_RU = """💜 Твои активные диалоги

Выбери с кем продолжить общение или начни новый диалог."""

HAS_DIALOGS_EN = """💜 Your active dialogs

Choose who to continue chatting with or start a new dialog."""

# No active dialogs
NO_DIALOGS_RU = """💌 У тебя пока нет активных диалогов.

Открой приложение — выбери персонажа и начни общение."""

NO_DIALOGS_EN = """💌 You don't have any active dialogs yet.

Open the app — choose a character and start chatting."""

# Daily limit reached
LIMIT_REACHED_RU = """⏸ <b>Дневной лимит исчерпан</b>

Ты использовал все {limit} бесплатных сообщений на сегодня.

Чтобы продолжить общение — оформи подписку 💎"""

LIMIT_REACHED_EN = """⏸ <b>Daily limit reached</b>

You've used all {limit} free messages for today.

To continue chatting — get a subscription 💎"""


# ==================== KEYBOARDS ====================

def format_dialog_date(dt: datetime | None) -> str:
    """Format dialog date for display"""
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    return dt.strftime("%d.%m")


STORY_TITLES_EN = {
    "lina": {
        "sauna_support": "Sauna After Workout",
        "shower_flirt": "The Broken Shower",
        "gym_late": "Late Night at the Gym",
        "competition_prep": "Competition Prep",
    },
    "marianna": {
        "support": "Night Echo",
        "cozy": "A Game of Trust",
        "flirt": "Secret Getaway",
        "serious": "Adults-Only Hotel",
    },
    "mei": {
        "mall_bench": "Meeting at the Mall",
        "car_ride": "Car Ride",
        "home_visit": "At Your Place",
        "regular_visits": "Regular Visits",
    },
    "stacey": {
        "rooftop_sunset": "Evening on the Rooftop",
        "hints_game": "The Game of Hints and Riddles",
        "confession": "Unexpected Confession After a Walk",
        "night_park": "Night Adventure in the Empty Park",
    },
    "yuna": {
        "first_evening": "First Evening",
        "city_lights": "Walk Through the City Lights",
        "tea_secrets": "Tea and Secrets",
    },
    "taya": {
        "bar_back_exit": "Bar's Back Exit",
        "gaming_center": "Gaming Center",
        "friends_wife": "Alone with a Friend's Wife",
        "office_elevator": "Office Story",
    },
    "julie": {
        "home_tutor": "Home Tutor",
        "teacher_punishment": "Teacher Disciplines After Class",
        "bus_fun": "Fun on the Bus",
    },
    "ash": {
        "living_room": "In the Living Room",
        "bedroom": "In the Bedroom",
    },
    "anastasia": {
        "classroom": "Daddy and the Teacher in Classroom",
        "bathroom": "Teacher Locked Herself with Daddy in the Bathroom",
    },
    "sasha": {
        "auction": "Unusual Dates Auction",
        "plane": "Incident in First Class",
        "party": "Someone Else's Girl",
    },
    "roxy": {
        "hitchhiker": "Hitchhiker",
        "maid": "The Maid",
        "beach": "On the Beach",
    },
    "pai": {
        "dinner": "Dinner with More to Come",
        "window": "By the Bedroom Window",
        "car": "Payment in Kind",
    },
    "hani": {
        "photoshoot": "Photo Session",
        "pool": "Alone in the Pool",
        "elevator": "Meeting in the Elevator",
    },
}


def get_story_title_en(persona_key: str, story_key: str) -> str | None:
    """Get English story title"""
    return STORY_TITLES_EN.get(persona_key, {}).get(story_key)


def get_story_title(persona_key: str, story_key: str) -> str | None:
    """Get story title from persona stories"""
    try:
        persona_data = PERSONAS.get(persona_key)
        if not persona_data or "stories" not in persona_data:
            return None

        story = persona_data["stories"].get(story_key)
        if story and "title" in story:
            return story["title"]
        return None
    except Exception:
        return None


def get_dialogs_keyboard_ru(dialogs: list[Dialog], can_create_new: bool = True) -> InlineKeyboardMarkup:
    """Build keyboard with active dialogs (Russian)"""
    buttons = []

    # New dialog button (if less than 5 active)
    if can_create_new:
        if config.webapp_url:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ Новый диалог • Персонажи",
                    web_app=WebAppInfo(url=config.webapp_url)
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ Новый диалог • Персонажи",
                    callback_data="menu:open_webapp"
                )
            ])

    # Dialog buttons
    for dialog in dialogs:
        persona_name = "Персонаж"
        if dialog.persona:
            persona_name = dialog.persona.name

        date_str = format_dialog_date(dialog.updated_at or dialog.created_at)

        # Build label: Name • Date • Story
        label = f"💬 {persona_name}"
        if date_str:
            label += f" • {date_str}"

        # Add story title if exists
        if dialog.story_id and dialog.persona:
            story_title = get_story_title(dialog.persona.key, dialog.story_id)
            if story_title:
                # Truncate to first 15 chars + "..."
                truncated = story_title[:15] + "..." if len(story_title) > 15 else story_title
                label += f" • {truncated}"

        # Dialog button + Delete button in one row
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"chat:continue:{dialog.id}"
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"chat:delete:{dialog.id}"
            )
        ])

    # Clear all button (only if there are dialogs)
    if dialogs:
        buttons.append([
            InlineKeyboardButton(text="🗑 Очистить диалоги", callback_data="chat:clear_all")
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="chat:back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dialogs_keyboard_en(dialogs: list[Dialog], can_create_new: bool = True) -> InlineKeyboardMarkup:
    """Build keyboard with active dialogs (English)"""
    buttons = []

    # New dialog button (if less than 5 active)
    if can_create_new:
        if config.webapp_url:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ New dialog • Characters",
                    web_app=WebAppInfo(url=config.webapp_url)
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="➕ New dialog • Characters",
                    callback_data="menu:open_webapp"
                )
            ])

    # Dialog buttons
    for dialog in dialogs:
        persona_name = "Character"
        if dialog.persona:
            persona_name = PERSONA_KEY_TO_EN_NAME.get(dialog.persona.key, dialog.persona.name) if dialog.persona.key else dialog.persona.name

        date_str = format_dialog_date(dialog.updated_at or dialog.created_at)

        # Build label: Name • Date • Story
        label = f"💬 {persona_name}"
        if date_str:
            label += f" • {date_str}"

        # Add story title if exists
        if dialog.story_id and dialog.persona:
            story_title = get_story_title_en(dialog.persona.key, dialog.story_id)
            if story_title:
                # Truncate to first 15 chars + "..."
                truncated = story_title[:15] + "..." if len(story_title) > 15 else story_title
                label += f" • {truncated}"

        # Dialog button + Delete button in one row
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"chat:continue:{dialog.id}"
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"chat:delete:{dialog.id}"
            )
        ])

    # Clear all button (only if there are dialogs)
    if dialogs:
        buttons.append([
            InlineKeyboardButton(text="🗑 Clear dialogs", callback_data="chat:clear_all")
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="chat:back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_no_dialogs_keyboard_ru() -> InlineKeyboardMarkup:
    """Keyboard when no active dialogs (Russian)"""
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="Открыть CraveMe 💜",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="Открыть CraveMe 💜",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [webapp_btn],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="chat:back_to_menu")]
    ])


def get_no_dialogs_keyboard_en() -> InlineKeyboardMarkup:
    """Keyboard when no active dialogs (English)"""
    if config.webapp_url:
        webapp_btn = InlineKeyboardButton(
            text="Open CraveMe 💜",
            web_app=WebAppInfo(url=config.webapp_url)
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="Open CraveMe 💜",
            callback_data="menu:open_webapp"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [webapp_btn],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="chat:back_to_menu")]
    ])


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


async def get_active_dialogs_with_personas(user_id: int) -> list[Dialog]:
    """Get active dialogs with persona info loaded"""
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.user_id == user_id, Dialog.is_active == True)
            .order_by(Dialog.updated_at.desc())
            .limit(10)
        )
        return list(result.scalars().all())
    return []


async def check_message_limit(user_id: int, lang: str) -> tuple[bool, str | None]:
    """
    Check if user can send a message (free users have 20 messages/day limit).
    Uses Redis for fast counter with automatic daily reset.
    Returns (can_send, error_message)
    """
    # Check subscription status from DB
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


# ==================== HANDLERS ====================

async def _show_chat_screen(user_id: int, target):
    """Common logic for showing chat screen"""
    lang = await get_user_language(user_id)
    dialogs = await get_active_dialogs_with_personas(user_id)

    if dialogs:
        # User has dialogs - show with photo
        can_create_new = len(dialogs) < 10
        if lang == "ru":
            text = HAS_DIALOGS_RU
            keyboard = get_dialogs_keyboard_ru(dialogs, can_create_new)
        else:
            text = HAS_DIALOGS_EN
            keyboard = get_dialogs_keyboard_en(dialogs, can_create_new)
        logger.info(f"User {user_id} has {len(dialogs)} active dialog(s)")

        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # No dialogs - show without photo
        if lang == "ru":
            text = NO_DIALOGS_RU
            keyboard = get_no_dialogs_keyboard_ru()
        else:
            text = NO_DIALOGS_EN
            keyboard = get_no_dialogs_keyboard_en()
        logger.info(f"User {user_id} has no active dialogs")

        await target.answer(text, reply_markup=keyboard)


@router.message(Command("chat"))
async def cmd_chat(message: Message):
    """Handle /chat command - start chat section"""
    await _show_chat_screen(message.from_user.id, message)
    logger.info(f"User {message.from_user.id} opened chat via /chat command")


@router.callback_query(F.data == "menu:start_chat")
async def on_start_chat(callback: CallbackQuery):
    """Handle 'Start Chat' button from main menu"""
    await callback.answer()
    await _show_chat_screen(callback.from_user.id, callback.message)


@router.callback_query(F.data.startswith("chat:continue:"))
async def on_continue_dialog(callback: CallbackQuery):
    """Handle 'Continue' button - resume specific dialog"""
    await callback.answer()
    user_id = callback.from_user.id

    # Get user language
    lang = await get_user_language(user_id)

    # Check message limit BEFORE continuing dialog
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
        await callback.message.answer(error_msg, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"User {user_id} reached daily message limit when continuing dialog")
        return

    # Extract dialog_id from callback data
    dialog_id = int(callback.data.split(":")[-1])

    # Get dialog with persona
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.id == dialog_id, Dialog.user_id == user_id)
        )
        dialog = result.scalar_one_or_none()

        if not dialog:
            await callback.message.answer("❌ Диалог не найден")
            return

        persona_name = dialog.persona.name if dialog.persona else "Персонаж"
        persona_id = dialog.persona_id

        # Show "generating" message
        await callback.message.answer(
            f"💬 Продолжаем общение с <b>{persona_name}</b>...",
            parse_mode="HTML"
        )

        # Generate return greeting via API (will be sent to Telegram by API)
        from app.services.api_client import generate_greeting
        result = await generate_greeting(
            telegram_id=user_id,
            persona_id=persona_id,
            story_id=dialog.story_id,
            atmosphere=dialog.atmosphere,
            is_return=True,
            send_to_telegram=True,  # API will send greeting to Telegram
        )

        if not result.success:
            logger.warning(f"Failed to generate greeting for user {user_id}: {result.error}")
            # Fallback - just tell user to write
            await callback.message.answer(
                "Напиши сообщение, чтобы продолжить 💬",
                parse_mode="HTML"
            )

        logger.info(f"User {user_id} continuing dialog {dialog_id} with {persona_name}")
        break


@router.callback_query(F.data.startswith("chat:delete:"))
async def on_delete_dialog(callback: CallbackQuery):
    """Handle delete dialog button - show confirmation"""
    await callback.answer()
    user_id = callback.from_user.id

    # Extract dialog_id from callback data
    dialog_id = int(callback.data.split(":")[-1])

    # Get dialog info for confirmation message
    async for db in get_db():
        result = await db.execute(
            select(Dialog)
            .options(selectinload(Dialog.persona))
            .where(Dialog.id == dialog_id, Dialog.user_id == user_id)
        )
        dialog = result.scalar_one_or_none()

        if not dialog:
            await callback.answer("❌ Диалог не найден", show_alert=True)
            return

        persona_name = dialog.persona.name if dialog.persona else "Персонаж"
        lang = await get_user_language(user_id)

        # Confirmation message
        if lang == "ru":
            text = f"🗑 Удалить диалог с <b>{persona_name}</b>?\n\nВся история переписки будет удалена безвозвратно."
            confirm_btn_text = "✅ Да, удалить"
            cancel_btn_text = "❌ Отмена"
        else:
            text = f"🗑 Delete dialog with <b>{persona_name}</b>?\n\nAll chat history will be permanently deleted."
            confirm_btn_text = "✅ Yes, delete"
            cancel_btn_text = "❌ Cancel"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=confirm_btn_text,
                    callback_data=f"chat:delete_confirm:{dialog_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=cancel_btn_text,
                    callback_data="chat:delete_cancel"
                )
            ]
        ])

        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        break


@router.callback_query(F.data.startswith("chat:delete_confirm:"))
async def on_delete_confirm(callback: CallbackQuery):
    """Handle delete confirmation - actually delete the dialog"""
    await callback.answer()
    user_id = callback.from_user.id

    # Extract dialog_id from callback data
    dialog_id = int(callback.data.split(":")[-1])

    async for db in get_db():
        # Get dialog
        result = await db.execute(
            select(Dialog)
            .where(Dialog.id == dialog_id, Dialog.user_id == user_id)
        )
        dialog = result.scalar_one_or_none()

        if not dialog:
            await callback.message.edit_text("❌ Диалог не найден")
            return

        # Delete from PostgreSQL (cascade will delete messages)
        await db.delete(dialog)
        await db.commit()

        # Delete from Qdrant
        try:
            qdrant_url = config.qdrant_url if hasattr(config, 'qdrant_url') else "http://qdrant:6333"
            collection = "vitte_memories"

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{qdrant_url}/collections/{collection}/points/delete",
                    json={
                        "filter": {
                            "must": [
                                {"key": "user_id", "match": {"value": user_id}},
                                {"key": "dialog_id", "match": {"value": dialog_id}},
                            ]
                        }
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning(f"Failed to delete Qdrant memories for dialog {dialog_id}: {e}")

        lang = await get_user_language(user_id)

        # Success message
        if lang == "ru":
            success_text = "✅ Диалог удалён"
        else:
            success_text = "✅ Dialog deleted"

        await callback.message.edit_text(success_text)

        # Show updated dialogs list
        await _show_chat_screen(user_id, callback.message)

        logger.info(f"User {user_id} deleted dialog {dialog_id}")
        break


@router.callback_query(F.data == "chat:delete_cancel")
async def on_delete_cancel(callback: CallbackQuery):
    """Handle delete cancellation"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = "Отменено"
    else:
        text = "Cancelled"

    await callback.message.edit_text(text)

    # Show dialogs list again
    await _show_chat_screen(user_id, callback.message.answer)


@router.callback_query(F.data == "chat:clear_all")
async def on_clear_all_dialogs(callback: CallbackQuery):
    """Handle clear all dialogs button - show confirmation"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    if lang == "ru":
        text = "🗑 Удалить <b>все</b> диалоги?\n\nВся история переписки будет удалена безвозвратно."
        confirm_btn_text = "✅ Да, удалить все"
        cancel_btn_text = "❌ Отмена"
    else:
        text = "🗑 Delete <b>all</b> dialogs?\n\nAll chat history will be permanently deleted."
        confirm_btn_text = "✅ Yes, delete all"
        cancel_btn_text = "❌ Cancel"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=confirm_btn_text, callback_data="chat:clear_all_confirm")],
        [InlineKeyboardButton(text=cancel_btn_text, callback_data="chat:delete_cancel")],
    ])

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "chat:clear_all_confirm")
async def on_clear_all_confirm(callback: CallbackQuery):
    """Handle clear all confirmation - delete all user dialogs"""
    await callback.answer()
    user_id = callback.from_user.id

    async for db in get_db():
        # Get all active dialogs
        result = await db.execute(
            select(Dialog).where(Dialog.user_id == user_id, Dialog.is_active == True)
        )
        dialogs = list(result.scalars().all())

        if not dialogs:
            await callback.message.edit_text("Нет диалогов для удаления")
            return

        dialog_ids = [d.id for d in dialogs]

        # Delete all from PostgreSQL (cascade deletes messages)
        for dialog in dialogs:
            await db.delete(dialog)
        await db.commit()

        # Delete all from Qdrant
        try:
            qdrant_url = config.qdrant_url if hasattr(config, 'qdrant_url') else "http://qdrant:6333"
            collection = "vitte_memories"

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{qdrant_url}/collections/{collection}/points/delete",
                    json={
                        "filter": {
                            "must": [
                                {"key": "user_id", "match": {"value": user_id}},
                            ]
                        }
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning(f"Failed to delete Qdrant memories for user {user_id}: {e}")

        lang = await get_user_language(user_id)
        if lang == "ru":
            success_text = f"✅ Удалено диалогов: {len(dialog_ids)}"
        else:
            success_text = f"✅ Deleted dialogs: {len(dialog_ids)}"

        await callback.message.edit_text(success_text)

        # Show updated (empty) dialogs list
        await _show_chat_screen(user_id, callback.message)

        logger.info(f"User {user_id} cleared all dialogs: {dialog_ids}")
        break


@router.callback_query(F.data == "chat:back_to_menu")
async def on_back_to_menu(callback: CallbackQuery):
    """Handle 'Back' button - return to main menu"""
    await callback.answer()

    # Import here to avoid circular imports
    from app.handlers.menu import show_main_menu

    user_id = callback.from_user.id
    lang = await get_user_language(user_id)

    await show_main_menu(callback, lang=lang)

    logger.info(f"User {user_id} returned to main menu from chat")
