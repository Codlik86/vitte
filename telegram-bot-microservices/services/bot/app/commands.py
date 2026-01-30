"""
Bot commands registration

Sets up the menu button commands that appear when user clicks
the menu button (left of input field).
"""
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

from shared.utils import get_logger

logger = get_logger(__name__)


# ==================== COMMANDS ====================

COMMANDS_RU = [
    BotCommand(command="menu", description="📋 Главное меню"),
    BotCommand(command="chat", description="💕 Начать общение"),
    BotCommand(command="app", description="💌 Открыть приложение"),
]

COMMANDS_EN = [
    BotCommand(command="menu", description="📋 Main Menu"),
    BotCommand(command="chat", description="💕 Start Chat"),
    BotCommand(command="app", description="💌 Open App"),
]


# ==================== SETUP ====================

async def setup_bot_commands(bot: Bot):
    """
    Register bot commands for menu button.
    Called once at bot startup.
    """
    # Set Russian commands as default (for all private chats)
    await bot.set_my_commands(
        commands=COMMANDS_RU,
        scope=BotCommandScopeAllPrivateChats()
    )

    # Set English commands for English language
    await bot.set_my_commands(
        commands=COMMANDS_EN,
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en"
    )

    logger.info("Bot commands registered (RU default, EN for English users)")
