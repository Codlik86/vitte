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

from .config import settings
from .db import get_session
from .logging_config import logger
from .models import User
from .middlewares.access import AccessMiddleware
from .middlewares.terms_gate import TermsGateMiddleware
from .services.chat_flow import generate_chat_reply
from .services.features import unlock_feature, collect_feature_states
from .services.onboarding import (
    build_terms_keyboard,
    onboarding_text,
    intro_text,
    help_text,
)
from .services.stars import send_stars_invoice_for_subscription, send_stars_invoice_for_feature
from .services.subscriptions import ensure_premium_for_user, get_user_subscription_status
from .services.telegram_id import get_debug_telegram_id
from .users_service import get_or_create_user_by_telegram_id
from .utils.async_helpers import ensure_async_iter
from .services.store import SUBSCRIPTION_PLANS, IMAGE_PACKS, EMOTIONAL_FEATURES, get_plan, get_image_pack, get_feature
from .services.image_quota import _ensure_balance

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()
dp.update.middleware(TermsGateMiddleware())
dp.update.middleware(AccessMiddleware())

STAR_MULTIPLIER = 1_000_000_000  # 1 XTR minimal units


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="app", description="Открыть мини-приложение"),
        BotCommand(command="pay", description="Оплата и подписка"),
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


def pay_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписка", callback_data="pay_menu:subs")],
            [InlineKeyboardButton(text="Изображения", callback_data="pay_menu:images")],
            [
                InlineKeyboardButton(
                    text="Купить ⭐ у Telegram",
                    url="https://t.me/PremiumBot",
                )
            ],
        ]
    )


def pay_subs_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for plan in SUBSCRIPTION_PLANS:
        label = f"{plan.duration_days} дн — {plan.price_stars}⭐"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"pay_sub:{plan.code}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="pay_menu:root")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pay_images_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for pack in IMAGE_PACKS:
        label = f"{pack.images} изображений — {pack.price_stars}⭐"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"pay_pack:{pack.code}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="pay_menu:root")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_pay_root(message: Message) -> None:
    text = (
        "Vitte\n"
        "Выбери, что хочешь оформить:\n\n"
        "• Подписка Vitte Plus\n"
        "• Дополнительные изображения\n"
        "• Купить звёзды у Telegram"
    )
    await message.answer(text, reply_markup=pay_root_keyboard())


async def send_pay_subs(message: Message, subscription_active: bool, until: datetime | None) -> None:
    lines = [
        "Подписка Vitte Plus",
        "Безлимит сообщений + 20 изображений в день.",
    ]
    if subscription_active:
        until_text = until.strftime("%d.%m.%Y") if until else "без даты окончания"
        lines.append(f"Активна до {until_text}.")
    await message.answer("\n".join(lines), reply_markup=pay_subs_keyboard())


async def send_pay_images(message: Message) -> None:
    text = "Дополнительные изображения\nПокупай пакеты и трать, когда хочешь."
    await message.answer(text, reply_markup=pay_images_keyboard())


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
    await send_pay_root(message)


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

@dp.callback_query(F.data.startswith("pay_menu:"))
async def pay_menu(cb: CallbackQuery):
    if cb.message is None:
        return
    if cb.data == "pay_menu:root":
        await cb.message.edit_text(
            "Vitte\nВыбери, что хочешь оформить:\n\n• Подписка Vitte Plus\n• Дополнительные изображения\n• Купить звёзды у Telegram",
            reply_markup=pay_root_keyboard(),
        )
        return
    if cb.data == "pay_menu:subs":
        async for session in get_session():
            user = await get_or_create_user_by_telegram_id(session, cb.from_user.id)
            status = await get_user_subscription_status(session, user)
            await session.commit()
        await cb.message.edit_text(
            "Подписка Vitte Plus\nБезлимит сообщений + 20 изображений в день."
            + (f"\nАктивна до {status['until'].strftime('%d.%m.%Y')}" if status.get("has_subscription") else ""),
            reply_markup=pay_subs_keyboard(),
        )
        return
    if cb.data == "pay_menu:images":
        await cb.message.edit_text(
            "Дополнительные изображения\nПокупай пакеты и трать, когда хочешь.",
            reply_markup=pay_images_keyboard(),
        )
        return


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


@dp.callback_query(F.data.startswith("pay_sub:"))
async def pay_sub_selected(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    plan_code = cb.data.split(":", 1)[1]
    plan = get_plan(plan_code)
    if not plan:
        await cb.answer("Тариф не найден", show_alert=True)
        return
    try:
        await send_stars_invoice_for_subscription(
            bot,
            cb.message,
            plan_code=plan_code,
            price_rub=plan.price_stars,
        )
        await cb.answer("Счёт отправлен. Оплати в Stars.")
    except Exception as exc:
        logger.error("Failed to send stars invoice: %s", exc)
        await cb.answer("Не получилось создать счёт", show_alert=True)


@dp.callback_query(F.data.startswith("pay_pack:"))
async def pay_pack_selected(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    pack_code = cb.data.split(":", 1)[1]
    pack = get_image_pack(pack_code)
    if not pack:
        await cb.answer("Пакет не найден", show_alert=True)
        return
    try:
        await send_stars_invoice_for_feature(
            bot,
            cb.message,
            feature_code=pack.code,
            title="Пакет изображений",
            description=f"{pack.images} изображений",
            price_rub=pack.price_stars,
            payload_prefix="pack",
        )
    except Exception as exc:
        logger.error("Failed to send stars invoice for pack: %s", exc)
    await cb.answer("Счёт отправлен. Оплати в Stars.")


@dp.callback_query(F.data.startswith("pay_feat:"))
async def pay_feature_selected(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    feature_code = cb.data.split(":", 1)[1]
    feature = get_feature(feature_code)
    if not feature:
        await cb.answer("Улучшение не найдено", show_alert=True)
        return
    try:
        await send_stars_invoice_for_feature(
            bot,
            cb.message,
            feature_code=feature_code,
            title=feature.title,
            description=feature.description,
            price_rub=feature.price_stars,
        )
    except Exception as exc:
        logger.error("Failed to send stars invoice for feature %s: %s", feature_code, exc)
    await cb.answer("Счёт отправлен. Оплати в Stars.")


async def handle_update(update: dict):
    telegram_update = Update.model_validate(update)
    await dp.feed_update(bot, telegram_update)


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    if message.from_user is None or message.successful_payment is None:
        return
    payload = message.successful_payment.invoice_payload
    if not payload or ":" not in payload:
        return
    kind, code = payload.split(":", 1)
    try:
        async for session in get_session():
            user = await get_or_create_user_by_telegram_id(session, message.from_user.id)
            if kind == "sub":
                await ensure_premium_for_user(session, user, plan_code=code)
            elif kind == "pack":
                pack = get_image_pack(code)
                if pack:
                    balance = await _ensure_balance(session, user)
                    balance.total_purchased_images += pack.images
                    balance.remaining_purchased_images += pack.images
            elif kind == "feat":
                feature = get_feature(code)
                if feature:
                    await unlock_feature(session, user, feature_code=code)
            await session.commit()
    except Exception as exc:
        logger.error("Failed to apply payment %s:%s error=%s", kind, code, exc)
        return


# Further webhook binding is handled in main.py.
