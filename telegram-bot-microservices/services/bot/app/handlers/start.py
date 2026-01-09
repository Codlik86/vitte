"""
/start and /help command handlers
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import User, Subscription, get_db
from shared.utils import get_logger

logger = get_logger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    user = message.from_user
    
    try:
        # Get database session
        async for db in get_db():
            # Check if user exists
            result = await db.execute(
                select(User).where(User.id == user.id)
            )
            db_user = result.scalar_one_or_none()
            
            # Create user if not exists
            if not db_user:
                db_user = User(
                    id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code or "ru"
                )
                db.add(db_user)
                
                # Create free subscription
                subscription = Subscription(
                    user_id=user.id,
                    plan="free",
                    is_active=True,
                    messages_limit=100,
                    images_limit=10
                )
                db.add(subscription)
                
                await db.commit()
                logger.info(f"New user registered: {user.id}")
            
            break  # Exit async for loop
        
        # Send welcome message
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот Vitte - твой AI-ассистент.\n\n"
            "Используй /help для списка команд."
        )
        
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/status - Показать статус подписки\n\n"
        "Просто отправь мне сообщение, и я отвечу!"
    )
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command - show subscription status"""
    user = message.from_user
    
    try:
        async for db in get_db():
            # Get user subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                await message.answer("❌ Подписка не найдена. Используйте /start")
                break
            
            # Format subscription info
            status_text = (
                f"📊 <b>Ваша подписка:</b>\n\n"
                f"План: {subscription.plan}\n"
                f"Статус: {'✅ Активна' if subscription.is_active else '❌ Неактивна'}\n\n"
                f"<b>Лимиты:</b>\n"
                f"Сообщения: {subscription.messages_used}/{subscription.messages_limit}\n"
                f"Изображения: {subscription.images_used}/{subscription.images_limit}"
            )
            
            await message.answer(status_text, parse_mode="HTML")
            break
            
    except Exception as e:
        logger.error(f"Error in /status handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
