"""
Notification Service - отправка уведомлений пользователям

Отправляет уведомления когда пользователь давно не писал в диалог:
- 20 минут: приветливое
- 2 часа: чуть грустное
- 24 часа: грустит без юзера
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models import Dialog, Persona, NotificationLog, User
from shared.llm.personas.notification_templates import get_notification_text

logger = logging.getLogger(__name__)


def create_notification_keyboard(dialog_id: int) -> dict:
    """
    Создать клавиатуру с кнопками для уведомления.

    Args:
        dialog_id: ID диалога

    Returns:
        Inline keyboard markup
    """
    return {
        "inline_keyboard": [
            [
                {
                    "text": "💬 Начать общение",
                    "callback_data": f"chat:open:{dialog_id}"
                }
            ],
            [
                {
                    "text": "🏠 Главное меню",
                    "callback_data": "menu:main"
                }
            ]
        ]
    }


async def check_and_send_notifications(
    db: AsyncSession,
    send_telegram_message: Callable[[int, str, dict], Awaitable[Optional[int]]]
) -> int:
    """
    Проверить неактивные диалоги и отправить уведомления.

    Проверяет диалоги которые давно не обновлялись и отправляет
    уведомления согласно таймлайну (20 мин / 2 часа / 24 часа).

    Args:
        db: Database session
        send_telegram_message: Функция для отправки сообщения в Telegram
                               (chat_id, text, reply_markup) -> message_id

    Returns:
        Количество отправленных уведомлений
    """
    now = datetime.utcnow()
    sent_count = 0

    # Временные интервалы для уведомлений (минимальное время с момента последнего сообщения)
    intervals = [
        ("20min", timedelta(minutes=20)),   # После 20 минут неактивности
        ("2h", timedelta(hours=2)),          # После 2 часов неактивности
        ("24h", timedelta(hours=24)),        # После 24 часов неактивности
    ]

    for notification_type, min_delta in intervals:
        # Находим диалоги где прошло >= минимального времени
        threshold_time = now - min_delta

        result = await db.execute(
            select(Dialog, Persona, User)
            .join(Persona, Dialog.persona_id == Persona.id)
            .join(User, Dialog.user_id == User.id)
            .where(
                and_(
                    Dialog.is_active == True,
                    Dialog.updated_at <= threshold_time,  # Прошло >= min_delta времени
                )
            )
        )

        dialogs = result.all()

        for dialog, persona, user in dialogs:
            # Проверка 1: Не отправляли ли уже это уведомление
            existing_log = await db.execute(
                select(NotificationLog)
                .where(
                    and_(
                        NotificationLog.dialog_id == dialog.id,
                        NotificationLog.notification_type == notification_type,
                    )
                )
            )

            if existing_log.scalar_one_or_none():
                # Уже отправляли это уведомление для этого диалога
                continue

            # Проверка 2: Есть ли у пользователя более свежий активный диалог
            # (предотвращает спам от старых персонажей, если юзер общается с новым)
            latest_dialog_result = await db.execute(
                select(Dialog)
                .where(
                    and_(
                        Dialog.user_id == user.id,
                        Dialog.is_active == True,
                    )
                )
                .order_by(Dialog.updated_at.desc())
                .limit(1)
            )

            latest_dialog = latest_dialog_result.scalar_one_or_none()

            if latest_dialog and latest_dialog.id != dialog.id:
                # У пользователя есть более свежий диалог - не спамим от старого персонажа
                logger.debug(
                    f"Skipping notification for dialog {dialog.id} (user {user.id}): "
                    f"user has newer dialog {latest_dialog.id}"
                )
                continue

            # Получаем текст уведомления
            notification_text = get_notification_text(persona.key, notification_type)

            # Создаём клавиатуру
            keyboard = create_notification_keyboard(dialog.id)

            # Отправляем уведомление
            try:
                message_id = await send_telegram_message(
                    user.id,  # user.id это telegram_id
                    notification_text,
                    keyboard,
                )

                if message_id:
                    # Логируем отправку
                    notification_log = NotificationLog(
                        dialog_id=dialog.id,
                        user_id=user.id,
                        notification_type=notification_type,
                    )
                    db.add(notification_log)
                    await db.commit()

                    sent_count += 1
                    logger.info(
                        f"Notification sent: user_id={user.id}, dialog_id={dialog.id}, "
                        f"type={notification_type}, persona={persona.key}"
                    )
                else:
                    logger.warning(
                        f"Failed to send notification: user_id={user.id}, dialog_id={dialog.id}"
                    )

            except Exception as e:
                logger.error(
                    f"Error sending notification to user {user.id}: {e}",
                    exc_info=True
                )

    return sent_count


async def send_single_notification(
    db: AsyncSession,
    dialog_id: int,
    send_telegram_message: Callable[[int, str, dict], Awaitable[Optional[int]]],
    notification_type: str = "20min"
) -> bool:
    """
    Отправить одно уведомление для тестирования.

    Args:
        db: Database session
        dialog_id: ID диалога
        send_telegram_message: Функция для отправки сообщения в Telegram
        notification_type: Тип уведомления ('20min', '2h', '24h')

    Returns:
        True если отправлено успешно
    """
    # Получаем диалог с персонажем и пользователем
    result = await db.execute(
        select(Dialog, Persona, User)
        .join(Persona, Dialog.persona_id == Persona.id)
        .join(User, Dialog.user_id == User.id)
        .where(Dialog.id == dialog_id)
    )

    row = result.one_or_none()
    if not row:
        logger.error(f"Dialog {dialog_id} not found")
        return False

    dialog, persona, user = row

    # Получаем текст уведомления
    notification_text = get_notification_text(persona.key, notification_type)

    # Создаём клавиатуру
    keyboard = create_notification_keyboard(dialog.id)

    # Отправляем
    try:
        message_id = await send_telegram_message(
            user.telegram_id,
            notification_text,
            keyboard,
        )

        if message_id:
            logger.info(f"Test notification sent to user {user.id}, dialog {dialog_id}")
            return True

    except Exception as e:
        logger.error(f"Error sending test notification: {e}", exc_info=True)

    return False
