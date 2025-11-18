from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, Update

from .config import settings
from .logging_config import logger

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()


@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "Привет, я Vitte — романтический AI-компаньон. "
        "Скоро здесь будет полноценный диалог ❤️"
    )


async def handle_update(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


# Further webhook binding is handled in main.py.
