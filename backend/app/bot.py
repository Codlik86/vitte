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
    CallbackQuery,
    BotCommandScopeDefault,
    ReplyKeyboardRemove,
)
from datetime import datetime

import json
from aiogram.types import PreCheckoutQuery

from .config import settings
from .db import get_session
from .logging_config import logger
from .middlewares.access import AccessMiddleware
from .middlewares.terms_gate import TermsGateMiddleware
from .services.chat_flow import generate_chat_reply
from .services.features import apply_product_purchase
from .services.onboarding import (
    build_terms_keyboard,
    onboarding_text,
    intro_text,
    help_text,
)
from .services.payments import create_yookassa_payment_link
from .services.stars import send_stars_invoice_for_subscription
from .services.subscriptions import ensure_premium_for_user, get_user_subscription_status
from .services.telegram_id import get_debug_telegram_id
from .users_service import get_or_create_user_by_telegram_id
from .utils.async_helpers import ensure_async_iter

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()
dp.update.middleware(TermsGateMiddleware())
dp.update.middleware(AccessMiddleware())

STAR_MULTIPLIER = 1_000_000_000  # 1 XTR minimal units
PLAN_DURATIONS = {
    "sub_3d": 3,
    "sub_week": 7,
    "sub_month": 30,
    "sub_quarter": 90,
}


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="app", description="Открыть мини-приложение"),
        BotCommand(command="pay", description="Подписка"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="policy", description="Правила сервиса"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


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


def _format_plan_button(plan_code: str) -> InlineKeyboardButton:
    plan = SUBSCRIPTION_PLANS[plan_code]
    price_rub = plan.price_rub
    price_stars = plan.price_stars
    text = f"{plan.title} — {price_rub}₽ · {price_stars}⭐"
    return InlineKeyboardButton(text=text, callback_data=f"pay_plan:{plan_code}")


def pay_plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_format_plan_button("sub_3d")],
            [_format_plan_button("sub_week")],
            [_format_plan_button("sub_month")],
            [_format_plan_button("sub_quarter")],
            [
                InlineKeyboardButton(
                    text="Купить ⭐ у Telegram",
                    url="https://t.me/PremiumBot",
                )
            ],
        ]
    )


def pay_methods_keyboard(plan_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить звёздами ⭐",
                    callback_data=f"pay_stars:{plan_code}",
                )
            ],
        ]
    )


async def send_pay_intro(message: Message, user: User, status: dict):
    text = ""
    if status.get("has_subscription"):
        until = status.get("until")
        until_text = until.strftime("%d.%m.%Y") if until else "без срока"
        text = (
            f"Премиум Vitte активен до {until_text}.\n\n"
            "Премиум даёт:\n"
            "— безлимитные сообщения,\n"
            "— полный доступ к персонажам и историям,\n"
            "— улучшенные ответы.\n\n"
            "Хочешь продлить подписку?"
        )
    else:
        text = (
            "Премиум Vitte открывает:\n"
            "— общение без лимитов,\n"
            "— полный доступ к персонажам и улучшениям,\n"
            "— более глубокие и тёплые ответы.\n\n"
            "Выбери тариф:"
        )
    await message.answer(text, reply_markup=pay_plans_keyboard())


async def send_pay_intro_to_user(user: User, status: dict):
    if status.get("has_subscription"):
        until = status.get("until")
        until_text = until.strftime("%d.%m.%Y") if until else "без срока"
        text = (
            f"Премиум Vitte активен до {until_text}.\n\n"
            "Премиум даёт:\n"
            "— безлимитные сообщения,\n"
            "— полный доступ к персонажам и историям,\n"
            "— улучшенные ответы.\n\n"
            "Хочешь продлить подписку?"
        )
    else:
        text = (
            "Премиум Vitte открывает:\n"
            "— общение без лимитов,\n"
            "— полный доступ к персонажам и улучшениям,\n"
            "— более глубокие и тёплые ответы.\n\n"
            "Выбери тариф:"
        )
    await bot.send_message(user.telegram_id, text, reply_markup=pay_plans_keyboard())


@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user is None:
        return
    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, message.from_user.id)
        if not (user.accepted_terms_at and user.is_adult_confirmed):
            await message.answer(onboarding_text(), reply_markup=build_terms_keyboard())
            await session.commit()
            return
        await session.commit()
    await send_intro(message)


@dp.message(Command("app"))
async def cmd_app(message: Message):
    kb = build_miniapp_keyboard()
    await message.answer(
        "Чтобы открыть мини-приложение Vitte, нажми на кнопку ниже.",
        reply_markup=kb,
    )


@dp.message(F.text == "/pay")
async def cmd_pay(message: Message):
    if message.from_user is None:
        return
    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, message.from_user.id)
        status = await get_user_subscription_status(session, user)
        await session.commit()
    await send_pay_intro(message, user, status)


@dp.message(Command("help"))
async def cmd_help(message: Message, current_user: User | None = None):
    if message.from_user is None:
        return
    user = current_user
    if user is None:
        async for session in get_session():
            user = await get_or_create_user_by_telegram_id(session, message.from_user.id)
            await session.commit()
            break
    if user and user.accepted_terms_at and user.is_adult_confirmed:
        await message.answer(help_text(), reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(
            "Чтобы использовать Vitte, нужно подтвердить возраст 18+ и принять правила.",
            reply_markup=build_terms_keyboard(),
        )


@dp.message(Command("policy"))
async def cmd_policy(message: Message):
    await message.answer(
        "Правила сервиса Vitte: сервис 18+, виртуальное общение, без офлайн-встреч и эскорта. "
        "При использовании ты подтверждаешь совершеннолетие и согласие с условиями. "
        "Полный текст правил доступен в мини-приложении."
    )


@dp.callback_query(F.data == "onb_accept_terms")
async def on_accept_terms(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, cb.from_user.id)
        user.accepted_terms_at = datetime.utcnow()
        user.is_adult_confirmed = True
        user.age_confirmed = True
        await session.commit()
    try:
        await cb.message.edit_text("Спасибо! Ты подтвердил правила и возраст.")
    except Exception:
        pass
    await send_intro(cb.message)


@dp.callback_query(F.data == "onb_reject_terms")
async def on_reject_terms(cb: CallbackQuery):
    if cb.message is None:
        return
    await cb.message.answer(
        "Понимаю. Без согласия с правилами и подтверждения возраста сервис недоступен. "
        "Если передумаешь, набери /start.",
    )


async def send_intro(message: Message):
    try:
        await message.answer(intro_text(), reply_markup=ReplyKeyboardRemove())
    except Exception as exc:
        logger.error("Failed to send intro: %s", exc)


@dp.message(F.text & ~F.text.startswith("/"))
async def on_user_message(message: Message, current_user: User | None = None, db_session=None):
    if message.from_user is None:
        return
    telegram_id = message.from_user.id
    session_iter_raw = [db_session] if db_session is not None and current_user is not None else get_session()
    session_iter = ensure_async_iter(session_iter_raw)
    logger.debug(
        "on_user_message: session_iter type=%s, repr=%s",
        type(session_iter_raw),
        str(session_iter_raw)[:400],
    )
    async for session in session_iter:
        user = current_user or await get_or_create_user_by_telegram_id(session, telegram_id)
        if user.active_persona_id is None:
            await message.answer(
                "Выбери персонажа в мини-приложении, чтобы начать общение. "
                "Это нужно, чтобы приветствие и ответы были в стиле выбранного героя.",
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
            )
        except Exception as exc:
            logger.error("Failed to handle user message: %s", exc)
            await message.answer("Не получилось ответить, попробуй ещё раз или открой мини-приложение.")


@dp.callback_query(F.data.startswith("pay_plan:"))
async def pay_plan_selected(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    plan_code = cb.data.split(":", 1)[1]
    plan = SUBSCRIPTION_PLANS.get(plan_code)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return
    text = (
        f"Тариф «{plan.title}»\n"
        f"Цена: {plan.price_rub}₽ или {plan.price_stars}⭐️\n\n"
        "Оплатить можно через Telegram Stars."
    )
    await cb.message.answer(text, reply_markup=pay_methods_keyboard(plan_code))
    await cb.answer()


@dp.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(cb: CallbackQuery):
    if cb.from_user is None:
        return
    plan_code = cb.data.split(":", 1)[1]
    plan = SUBSCRIPTION_PLANS.get(plan_code)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return
    try:
        await send_stars_invoice_for_subscription(
            bot,
            cb.message,
            plan_code=plan_code,
            price_rub=plan.price_rub,
        )
        await cb.answer()
    except Exception as exc:
        logger.error("Failed to send stars invoice: %s", exc)
        await cb.answer("Не получилось создать счёт", show_alert=True)


@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    try:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as exc:
        logger.error("Pre-checkout failed: %s", exc)


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    if message.from_user is None:
        return
    success = message.successful_payment
    payload_raw = success.invoice_payload if success else ""
    currency = success.currency if success else ""
    product_code = None

    if currency == "XTR" and payload_raw:
        if payload_raw.startswith("sub:"):
            product_code = payload_raw.split(":", 1)[1]
        elif payload_raw.startswith("feat:"):
            product_code = f"feature_{payload_raw.split(':', 1)[1]}"
    if product_code is None:
        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = {}
        product_code = payload.get("product_code")

    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, message.from_user.id)
        if product_code and product_code.startswith("sub_"):
            days = PLAN_DURATIONS.get(product_code, 30)
            await ensure_premium_for_user(session, user, plan_code=product_code, period_days=days)
            await session.commit()
            await message.answer("Оплата получена! Подписка активирована. 💜")
        elif product_code and product_code.startswith("feature_"):
            try:
                apply_product_purchase(user, product_code.replace("feature_", ""))
            except Exception as exc:
                logger.error("Feature activation failed: %s", exc)
            await session.commit()
            await message.answer("Оплата получена! Улучшение активировано.")
        else:
            await message.answer("Оплата получена. Спасибо!")


async def handle_update(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


# Further webhook binding is handled in main.py.
