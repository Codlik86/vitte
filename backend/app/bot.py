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
)
from datetime import datetime

from .config import settings
from .logging_config import logger
from .middlewares.access import AccessMiddleware
from .middlewares.terms_gate import TermsGateMiddleware
from .services.chat_flow import generate_chat_reply
from .services.subscriptions import get_user_subscription_status, ensure_premium_for_user
from .billing.prices import SUBSCRIPTION_PLANS, FEATURE_PRICES_STARS
from .services.features import apply_product_purchase
from .services.telegram_id import get_debug_telegram_id
from .services.payments import create_yookassa_payment_link
from .db import get_session
from .users_service import get_or_create_user_by_telegram_id
from .services.onboarding import (
    build_terms_keyboard,
    onboarding_text,
    intro_text,
    help_text,
)
from .models import User
from aiogram.types import LabeledPrice, PreCheckoutQuery
import json

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
        BotCommand(command="pay", description="Подписка"),
        BotCommand(command="help", description="Помощь"),
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
            [
                InlineKeyboardButton(
                    text="Оплатить через YooKassa",
                    callback_data=f"pay_yk:{plan_code}",
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
    await message.answer(
        "Открываю мини-приложение Vitte 💌\n"
        "Через него можно оформить подписку и управлять персонажами.",
        reply_markup=build_miniapp_keyboard(),
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
        await message.answer(help_text(), reply_markup=build_miniapp_keyboard())
    else:
        await message.answer(
            "Чтобы использовать Vitte, нужно подтвердить возраст 18+ и принять правила.",
            reply_markup=build_terms_keyboard(),
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
        await message.answer(intro_text(), reply_markup=build_miniapp_keyboard())
    except Exception as exc:
        logger.error("Failed to send intro: %s", exc)


@dp.message(F.text & ~F.text.startswith("/"))
async def on_user_message(message: Message, current_user: User | None = None, db_session=None):
    if message.from_user is None:
        return
    telegram_id = message.from_user.id
    session_iter = [db_session] if db_session is not None and current_user is not None else get_session()
    async for session in session_iter:
        user = current_user or await get_or_create_user_by_telegram_id(session, telegram_id)
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
        "Выбери способ оплаты:"
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
    if not settings.stars_provider_token:
        await cb.message.answer(
            "Оплата звёздами временно недоступна. Попробуй YooKassa или чуть позже."
        )
        await cb.answer()
        return
    amount_units = plan.price_stars * STAR_MULTIPLIER
    payload = json.dumps({"product_code": plan_code})
    try:
        await bot.send_invoice(
            chat_id=cb.from_user.id,
            title=f"Подписка Vitte — {plan.title}",
            description="Премиум доступ к общению без лимитов и улучшенным ответам.",
            payload=payload,
            provider_token=settings.stars_provider_token,
            currency="XTR",
            prices=[LabeledPrice(label=plan.title, amount=amount_units)],
        )
        await cb.answer()
    except Exception as exc:
        logger.error("Failed to send stars invoice: %s", exc)
        await cb.answer("Не получилось создать счёт", show_alert=True)


@dp.callback_query(F.data.startswith("pay_yk:"))
async def pay_yk(cb: CallbackQuery):
    if cb.from_user is None:
        return
    plan_code = cb.data.split(":", 1)[1]
    plan = SUBSCRIPTION_PLANS.get(plan_code)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return
    # Заглушка YooKassa с попыткой ссылки
    link = await create_yookassa_payment_link(plan_code, cb.from_user.id)
    if link:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Оплатить в YooKassa", url=link)]]
        )
        await cb.message.answer(
            f"Тариф «{plan.title}» — {plan.price_rub}₽.\nОплатить через YooKassa:",
            reply_markup=kb,
        )
    else:
        await cb.message.answer(
            "Ссылка на оплату через YooKassa будет доступна чуть позже. "
            "Сейчас можно оформить подписку за звёзды внутри Telegram."
        )
    await cb.answer()


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
    payload_raw = message.successful_payment.invoice_payload if message.successful_payment else ""
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
