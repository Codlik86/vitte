"""
/help command handler

Shows available bot commands with i18n support.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_i18n import I18nContext

from shared.utils import get_logger

logger = get_logger(__name__)
router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(message: Message, i18n: I18nContext):
    """
    Handle /help command

    Shows list of available commands in user's language.
    """
    help_text = (
        f"{i18n.get('help-title')}\n\n"
        f"{i18n.get('help-start')}\n"
        f"{i18n.get('help-help')}\n"
        f"{i18n.get('help-status')}\n\n"
        f"{i18n.get('help-text')}"
    )

    await message.answer(help_text, parse_mode="HTML")
    logger.debug(f"Help shown to user {message.from_user.id}")
