"""
Bot initialization and configuration
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config
from app.handlers import start_router
from shared.utils import get_logger

logger = get_logger(__name__)


def create_bot() -> Bot:
    """Create and configure bot instance"""
    return Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with routers"""
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(start_router)
    
    logger.info("Bot dispatcher configured")
    return dp
