"""
/start command handler

Handles user registration and onboarding flow.
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
    ImageBalance,
)
from shared.utils import get_logger

# Константы лимитов для Free подписки
FREE_IMAGES_BONUS = 10  # Разовый бонус фото при регистрации
from app.handlers.onboarding import get_language_keyboard, WELCOME_TEXT

logger = get_logger(__name__)
router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, i18n: I18nContext):
    """
    Handle /start command

    New users: Show language selection -> onboarding flow
    Existing users: Show welcome back message

    UTM tracking: /start <utm_source>
    Example: /start ad_campaign_1
    """
    user = message.from_user
    is_new_user = False

    # Extract UTM source from command args
    # Format: /start utm_source or /start (no args)
    utm_source = None
    if message.text and len(message.text.split()) > 1:
        utm_source = message.text.split()[1]
        logger.info(f"UTM source detected: {utm_source} for user {user.id}")

    try:
        async for db in get_db():
            # Check if user exists (CACHED - 5 min TTL)
            db_user = await get_user_by_id(db, user.id)

            # Create user if not exists
            if not db_user:
                is_new_user = True
                db_user = await create_user(
                    db,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code or "ru",
                    utm_source=utm_source  # Save UTM on registration
                )

                # Create free subscription (auto-cached)
                await create_subscription(
                    db,
                    user_id=user.id,
                    plan="free",
                    is_active=True,
                    messages_limit=20,  # 20 сообщений в день для Free
                    images_limit=FREE_IMAGES_BONUS
                )

                # Create ImageBalance with free bonus images (разовый бонус)
                image_balance = ImageBalance(
                    user_id=user.id,
                    total_purchased_images=FREE_IMAGES_BONUS,
                    remaining_purchased_images=FREE_IMAGES_BONUS,
                    daily_subscription_quota=0,  # Free не имеет ежедневной квоты
                    daily_subscription_used=0
                )
                db.add(image_balance)
                await db.commit()

                utm_log = f" | UTM: {utm_source}" if utm_source else ""
                logger.info(f"New user registered: {user.id} (@{user.username}) with {FREE_IMAGES_BONUS} free images{utm_log}")

            break

        if is_new_user:
            # New user: start onboarding with language selection
            await message.answer(
                WELCOME_TEXT,
                reply_markup=get_language_keyboard()
            )
        else:
            # Existing user: show main menu
            from app.handlers.menu import show_main_menu
            await show_main_menu(message, lang="ru")

        logger.debug(f"Start command processed for user {user.id}, new={is_new_user}")

    except Exception as e:
        logger.error(f"Error in /start handler: {e}", exc_info=True)
        await message.answer(i18n.get("error-general"))
