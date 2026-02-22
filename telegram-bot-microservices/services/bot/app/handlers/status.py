"""
/status command handler

Shows user subscription status with i18n support.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_i18n import I18nContext

from shared.database import get_db, get_subscription_by_user_id
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="status")


@router.message(Command("status"))
async def cmd_status(message: Message, i18n: I18nContext):
    """
    Handle /status command - show subscription status with caching

    Displays:
    - Subscription plan
    - Active/inactive status
    - Usage limits (messages, images)
    """
    user = message.from_user

    try:
        async for db in get_db():
            # Get user subscription (CACHED - 1 hour TTL)
            subscription = await get_subscription_by_user_id(db, user.id)

            if not subscription:
                await message.answer(i18n.get("error-general"))
                break

            # Handle both dict (from cache) and SQLAlchemy object
            if isinstance(subscription, dict):
                is_active = subscription.get("is_active", False)
                plan = subscription.get("plan", "free")
                messages_used = subscription.get("messages_used", 0)
                messages_limit = subscription.get("messages_limit", 100)
                images_used = subscription.get("images_used", 0)
                images_limit = subscription.get("images_limit", 5)
            else:
                is_active = subscription.is_active
                plan = subscription.plan
                messages_used = subscription.messages_used
                messages_limit = subscription.messages_limit
                images_used = subscription.images_used
                images_limit = subscription.images_limit

            # Format subscription info with translations
            status_active = i18n.get("status-active") if is_active else i18n.get("status-inactive")

            status_text = (
                f"{i18n.get('status-title')}\n\n"
                f"{i18n.get('status-plan', plan=plan)}\n"
                f"{status_active}\n\n"
                f"{i18n.get('status-limits')}\n"
                f"{i18n.get('status-messages', used=messages_used, limit=messages_limit)}\n"
                f"{i18n.get('status-images', used=images_used, limit=images_limit)}"
            )

            await message.answer(status_text, parse_mode="HTML")
            logger.debug(f"Status shown to user {user.id}: plan={plan}, active={is_active}")
            break

    except Exception as e:
        logger.error(f"Error in /status handler: {e}", exc_info=True)
        await message.answer(i18n.get("error-general"))
