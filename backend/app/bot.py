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
from .services.chat_flow import generate_chat_reply
from .db import get_session
from .users_service import get_or_create_user_by_telegram_id

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


@dp.message(F.text & ~F.text.startswith("/"))
async def on_user_message(message: Message):
    if message.from_user is None:
        return
    telegram_id = message.from_user.id
    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, telegram_id)
        if user.active_persona_id is None:
            await message.answer(
                "Выбери персонажа в мини-приложении, чтобы начать общение. "
                "Это нужно, чтобы приветствие и ответы были в стиле выбранного героя.",
                reply_markup=build_miniapp_keyboard(),
            )
            continue
        try:
            result = await generate_chat_reply(
                session=session,
                user=user,
                input_text=message.text or "",
                mode="default",
                skip_limits=True,  # AccessMiddleware уже ограничил
                skip_increment=True,  # уже инкрементировано в middleware
            )
            await message.answer(result.reply)
        except PermissionError:
            await message.answer(
                "Похоже, бесплатный лимит исчерпан. Открой мини-приложение Vitte, чтобы оформить подписку.",
                reply_markup=build_miniapp_keyboard(),
            )
        except Exception as exc:
            logger.error("Failed to handle user message: %s", exc)
            await message.answer("Не получилось ответить, попробуй ещё раз или открой мини-приложение.")


async def handle_update(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


# Further webhook binding is handled in main.py.
