"""
Main entry point for the Telegram bot
"""
import asyncio
from app.bot import create_bot, create_dispatcher
from app.config import config
from shared.database import init_db, close_db
from shared.utils import get_logger

logger = get_logger(__name__, config.log_level)


async def main():
    """Main bot function"""
    logger.info(f"Starting Vitte bot in {config.environment} mode...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Create bot and dispatcher
    bot = create_bot()
    dp = create_dispatcher()
    
    try:
        # Start bot
        logger.info("Bot started successfully")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # Cleanup
        await bot.session.close()
        await close_db()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
