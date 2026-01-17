"""
Bot initialization and configuration
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config
from app.handlers import start_router, help_router, status_router, onboarding_router, menu_router, chat_router, subscription_router
from app.middlewares import ThrottlingMiddleware, AntiFloodMiddleware, i18n_middleware
from shared.utils import get_logger

logger = get_logger(__name__)


def create_bot() -> Bot:
    """Create and configure bot instance"""
    return Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with routers and middlewares"""
    dp = Dispatcher()

    # Register middlewares (order matters!)
    # 1. i18n - must be FIRST to provide translation context to all handlers
    i18n_middleware.setup(dispatcher=dp)

    # 2. Anti-flood - strict protection (3 requests per 5 seconds)
    dp.message.middleware(AntiFloodMiddleware(
        limit=config.antiflood_limit,
        window=config.antiflood_window
    ))

    # 3. Throttling - normal rate limiting
    dp.message.middleware(ThrottlingMiddleware(
        message_limit=config.rate_limit_messages,
        message_window=config.rate_limit_messages_window,
        callback_limit=config.rate_limit_callbacks,
        callback_window=config.rate_limit_callbacks_window
    ))

    # Register callback query middlewares
    dp.callback_query.middleware(ThrottlingMiddleware(
        message_limit=config.rate_limit_messages,
        message_window=config.rate_limit_messages_window,
        callback_limit=config.rate_limit_callbacks,
        callback_window=config.rate_limit_callbacks_window
    ))

    # Register routers
    dp.include_router(start_router)
    dp.include_router(onboarding_router)
    dp.include_router(menu_router)
    dp.include_router(chat_router)
    dp.include_router(subscription_router)
    dp.include_router(help_router)
    dp.include_router(status_router)

    logger.info("Bot dispatcher configured with i18n, middlewares and routers")
    return dp
