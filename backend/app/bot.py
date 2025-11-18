from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    BotCommand,
)

from .config import settings
from .logging_config import logger
from .middlewares.access import AccessMiddleware

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()
dp.update.middleware(AccessMiddleware())


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать общение"),
        BotCommand(command="app", description="Открыть мини-приложение Vitte"),
        BotCommand(command="pay", description="Подписка и оплата"),
        BotCommand(command="help", description="Что умеет Vitte"),
    ]
    await bot.set_my_commands(commands)


def build_miniapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Vitte 💌",
                    web_app=WebAppInfo(url=settings.miniapp_url),
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет, я Vitte — романтический AI-компаньон 💌\n\n"
        "Этот сервис предназначен только для людей старше 18 лет.\n"
        "Продолжая пользоваться ботом, ты подтверждаешь, что тебе уже есть 18.\n\n"
        f"У тебя будет {settings.free_messages_limit} бесплатных сообщений, чтобы попробовать общение. "
        "После этого можно будет оформить подписку и продолжать без ограничений.\n\n"
        "Можешь писать прямо сюда или открыть мини-приложение."
    )
    await message.answer(text, reply_markup=build_miniapp_keyboard())


@dp.message(Command("app"))
async def cmd_app(message: Message):
    await message.answer(
        "Открываю мини-приложение Vitte 💌\n"
        "Через него можно оформить подписку и управлять персонажами.",
        reply_markup=build_miniapp_keyboard(),
    )


@dp.message(F.text == "/pay")
async def cmd_pay(message: Message):
    await message.answer(
        "Чтобы оформить подписку и продолжить общение без лимитов, "
        "открой мини-приложение Vitte в Telegram или вкладку Paywall.\n\n"
        "Поддержка Stars и YooKassa появится чуть позже, а пока это заглушка.",
    )


async def handle_update(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


# Further webhook binding is handled in main.py.
