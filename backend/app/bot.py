import asyncio

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
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime

from .config import settings
from .db import get_session
from .logging_config import logger
from sqlalchemy import text

from .models import User, Persona
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
from .utils.telegram_actions import ChatActionHandle, start_chat_action, stop_chat_action
from .services.image_generation import ImageRequestError, request_image_on_demand
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
AUTO_CONTINUE_PROMPT = "Продолжи диалог от лица персонажа, логично развивая текущую сцену."


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

def _continuation_lock_key(user_id: int, persona_id: int) -> int:
    return (int(user_id) << 20) + int(persona_id)


async def _try_acquire_continuation_lock(session, key: int) -> bool:
    try:
        result = await session.execute(text("SELECT pg_try_advisory_lock(:key) AS locked"), {"key": key})
        row = result.fetchone()
        return bool(row and row[0])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Continuation lock unavailable: %s", exc)
        return False


async def _release_continuation_lock(session, key: int) -> None:
    try:
        await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    except Exception as exc:  # noqa: BLE001
        logger.debug("Continuation unlock failed (ignored): %s", exc)


def build_image_button(persona_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👁️ Посмотреть", callback_data=f"img:{persona_id}"),
                InlineKeyboardButton(text="Продолжить", callback_data=f"img_hot:{persona_id}"),
            ]
        ]
    )


async def _safe_answer(cb: CallbackQuery, text: str, show_alert: bool = False) -> None:
    try:
        await cb.answer(text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        logger.warning("Callback answer failed (ignored): %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Callback answer unexpected error (ignored): %s", exc)


async def send_pay_intro_to_user(telegram_id: int) -> None:
    """
    Отправляет первый экран оплаты с кнопками Подписка / Изображения / Купить звёзды.
    """
    await bot.send_message(telegram_id, _pay_root_text(), reply_markup=pay_root_keyboard())


def _pay_root_text() -> str:
    return (
        "Vitte\n"
        "Выбери, что хочешь оформить:\n\n"
        "• Подписка Vitte Plus\n"
        "• Дополнительные изображения\n"
        "• Купить звёзды у Telegram"
    )


async def send_pay_root(message: Message) -> None:
    await message.answer(_pay_root_text(), reply_markup=pay_root_keyboard())


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
    if message.from_user is None:
        return
    await send_pay_intro_to_user(message.from_user.id)


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
    typing_handle: ChatActionHandle | None = None
    if message.chat:
        typing_handle = start_chat_action(bot, message.chat.id, "typing")
    session_iter_raw = [db_session] if db_session is not None and current_user is not None else get_session()
    session_iter = ensure_async_iter(session_iter_raw)
    logger.debug(
        "on_user_message: session_iter type=%s, repr=%s",
        type(session_iter_raw),
        str(session_iter_raw)[:400],
    )
    try:
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
                reply_markup = None
                if message.chat and getattr(message.chat, "type", None) == "private" and getattr(
                    settings, "image_enabled", False
                ):
                    reply_markup = build_image_button(result.persona_id)
                await message.answer(result.reply, reply_markup=reply_markup)
            except PermissionError:
                await message.answer(
                    "Похоже, бесплатный лимит исчерпан. Открой мини-приложение Vitte, чтобы оформить подписку.",
                )
            except Exception as exc:
                logger.error("Failed to handle user message: %s", exc)
                await message.answer("Не получилось ответить, попробуй ещё раз или открой мини-приложение.")
    finally:
        await stop_chat_action(typing_handle)


@dp.callback_query(F.data.startswith("img:"))
async def on_image_requested(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    try:
        persona_id = int(cb.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await _safe_answer(cb, "Некорректный запрос", show_alert=False)
        return

    await _safe_answer(cb, "Генерирую…")
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        # Не критично, если не удалось убрать кнопку.
        pass

    user_id: int | None = None
    async for session in get_session():
        user = await get_or_create_user_by_telegram_id(session, cb.from_user.id)
        await session.commit()
        user_id = user.id
        break

    if user_id is None:
        await cb.answer("Пользователь не найден", show_alert=False)
        return

    context = {
        "reply_text": (cb.message.text or cb.message.caption or "").strip(),
        "user_message": "",
    }

    upload_handle: ChatActionHandle | None = None
    status_message = None

    async def _on_generation_started() -> None:
        nonlocal upload_handle, status_message
        upload_handle = start_chat_action(bot, cb.message.chat.id, "upload_photo")
        try:
            status_message = await bot.send_message(cb.message.chat.id, "Отправляю фото✨")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to send upload status message: %s", exc)

    try:
        await request_image_on_demand(
            user_id=user_id,
            chat_id=cb.message.chat.id,
            persona_id=persona_id,
            bot_instance=bot,
            context=context,
            on_start=_on_generation_started,
        )
    except ImageRequestError as exc:
        if exc.reason == "no_quota":
            await _safe_answer(cb, "Лимит изображений закончился", show_alert=True)
        elif exc.reason == "disabled":
            await _safe_answer(cb, "Генерация изображений отключена", show_alert=False)
        elif exc.reason == "generation_failed":
            await _safe_answer(cb, "Не получилось сгенерировать изображение", show_alert=False)
        elif exc.reason == "busy":
            await _safe_answer(cb, "Давай дождёмся предыдущего фото 🙂", show_alert=False)
        else:
            await _safe_answer(cb, "Не получилось сгенерировать изображение", show_alert=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to handle image request: %s", exc)
        await _safe_answer(cb, "Не получилось сгенерировать изображение", show_alert=False)
    finally:
        await stop_chat_action(upload_handle)
        if status_message:
            try:
                await bot.delete_message(status_message.chat.id, status_message.message_id)
            except TelegramBadRequest:
                logger.debug("Temporary upload status message already gone")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to delete upload status message: %s", exc)


@dp.callback_query(F.data.startswith("img_hot:"))
async def on_image_hot_requested(cb: CallbackQuery):
    if cb.from_user is None or cb.message is None:
        return
    try:
        persona_id = int(cb.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await _safe_answer(cb, "Некорректный запрос", show_alert=False)
        return

    await _safe_answer(cb, "Продолжаю…", show_alert=False)

    typing_handle: ChatActionHandle | None = None
    if cb.message.chat:
        typing_handle = start_chat_action(bot, cb.message.chat.id, "typing")

    async for session in get_session():
        try:
            user = await get_or_create_user_by_telegram_id(session, cb.from_user.id)
            persona = await session.get(Persona, persona_id)
            if not persona:
                await cb.message.answer("Персонаж не найден.")
                break

            lock_key = _continuation_lock_key(user.id, persona.id)
            lock_acquired = await _try_acquire_continuation_lock(session, lock_key)
            if not lock_acquired:
                await cb.message.answer("Секунду, я думаю…")
                break

            try:
                result = await generate_chat_reply(
                    session=session,
                    user=user,
                    input_text=AUTO_CONTINUE_PROMPT,
                    persona_id=persona.id,
                    mode="auto_continue",
                    skip_limits=False,
                    skip_increment=False,
                    auto_continue=True,
                )
                reply_markup = None
                if cb.message.chat and getattr(cb.message.chat, "type", None) == "private" and getattr(
                    settings, "image_enabled", False
                ):
                    reply_markup = build_image_button(result.persona_id)
                await cb.message.answer(result.reply, reply_markup=reply_markup)
            finally:
                await _release_continuation_lock(session, lock_key)
            await session.commit()
        except PermissionError:
            await cb.message.answer(
                "Похоже, бесплатный лимит исчерпан. Открой мини-приложение Vitte, чтобы оформить подписку."
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to handle auto-continue: %s", exc)
            await cb.message.answer("Не получилось продолжить, попробуй ещё раз.")
        finally:
            await stop_chat_action(typing_handle)
        break


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
            price_stars=pack.price_stars,
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
            price_stars=feature.price_stars,
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
