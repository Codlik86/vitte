"""
/start command handler

Handles user registration and welcome message with i18n support.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_i18n import I18nContext

from shared.database import (
    get_db,
    get_user_by_id,
    create_user,
    create_subscription,
)
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, i18n: I18nContext):
    """
    Handle /start command with caching

    Actions:
    1. Check if user exists in database (cached, 5 min TTL)
    2. Create user if not exists
    3. Create free subscription for new users
    4. Send welcome message in user's language
    """
    user = message.from_user

    try:
        # Get database session
        async for db in get_db():
            # Check if user exists (CACHED - 5 min TTL)
            db_user = await get_user_by_id(db, user.id)

            # Create user if not exists
            if not db_user:
                db_user = await create_user(
                    db,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code or "ru"
                )

                # Create free subscription (auto-cached)
                await create_subscription(
                    db,
                    user_id=user.id,
                    plan="free",
                    is_active=True,
                    messages_limit=100,
                    images_limit=10
                )

                logger.info(f"New user registered: {user.id} (@{user.username})")

            break  # Exit async for loop

        # Send welcome message in user's language
        welcome_text = i18n.get("start-greeting", name=user.first_name)
        await message.answer(welcome_text)

        logger.debug(f"Start command processed for user {user.id}")

    except Exception as e:
        logger.error(f"Error in /start handler: {e}", exc_info=True)
        await message.answer(i18n.get("error-general"))
