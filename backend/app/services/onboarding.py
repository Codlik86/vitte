from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from ..config import settings


def build_terms_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Согласен", callback_data="onb_accept_terms"),
                InlineKeyboardButton(text="Не согласен", callback_data="onb_reject_terms"),
            ]
        ]
    )


def onboarding_text() -> str:
    return (
        "<b>Vitte — романтический AI-компаньон 18+</b>\n\n"
        "Это чат-сервис с виртуальными персонажами, эмоциями и романтикой. "
        "Только для совершеннолетних пользователей.\n\n"
        "Нажимая «Согласен», вы подтверждаете, что вам есть 18 лет и вы принимаете правила сервиса Vitte."
    )


def intro_text() -> str:
    return (
        "Добро пожаловать в Vitte 💜\n\n"
        "Это романтический AI-компаньон, который всегда на связи: можно делиться мыслями, "
        "получать тёплый отклик и переписываться как с онлайн-партнёром.\n\n"
        "В мини-приложении удобно выбирать героиню, оформлять подписку и включать улучшения общения.\n\n"
        "Есть ежедневный бесплатный лимит сообщений и расширенный доступ по подписке.\n\n"
        "Чтобы продолжить, нажми «Открыть Vitte 💌» или воспользуйся командами в правом меню."
    )


def help_text() -> str:
    return (
        "Vitte — романтический AI-компаньон 18+.\n\n"
        "Здесь ты можешь:\n"
        "— общаться с виртуальными персонажами,\n"
        "— делиться мыслями и получать тёплый отклик,\n"
        "— строить отношения по переписке в безопасном пространстве.\n\n"
        "В Mini App ты выбираешь героиню, управляешь подпиской и улучшениями общения.\n\n"
        "Чтобы начать, нажми «Открыть Vitte 💌» или открой мини-приложение в Telegram."
    )


def build_main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Открыть Vitte 💌",
                    web_app=WebAppInfo(url=settings.miniapp_url),
                )
            ]
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
