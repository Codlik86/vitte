"""
Broadcast tasks for sending mass notifications
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_, func

from app.celery_app import celery_app
from shared.database import (
    AsyncSessionLocal,
    User,
    Broadcast,
    BroadcastLog,
    BroadcastType,
    BroadcastStatus,
    ImageBalance,
)
from shared.utils import get_logger
from shared.notifications.telegram import send_telegram_notification

logger = get_logger(__name__)

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def send_broadcast_message(
    user_id: int,
    text: str,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
    buttons: Optional[List[dict]] = None,
) -> tuple[bool, Optional[str]]:
    """
    Отправить сообщение рассылки пользователю

    Returns:
        (success, error_message)
    """
    import httpx

    if not BOT_TOKEN:
        return False, "BOT_TOKEN not configured"

    telegram_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # Подготовка reply_markup если есть кнопки
    reply_markup = None
    if buttons:
        inline_keyboard = []
        for btn in buttons:
            inline_keyboard.append([{
                "text": btn.get("text", ""),
                "callback_data": btn.get("callback_data", "")
            }])
        reply_markup = {"inline_keyboard": inline_keyboard}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Отправка в зависимости от типа медиа
            if media_url and media_type == "photo":
                data = {
                    "chat_id": user_id,
                    "photo": media_url,
                    "caption": text,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    data["reply_markup"] = reply_markup

                response = await client.post(
                    f"{telegram_api_url}/sendPhoto",
                    json=data
                )

            elif media_url and media_type == "video":
                data = {
                    "chat_id": user_id,
                    "video": media_url,
                    "caption": text,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    data["reply_markup"] = reply_markup

                response = await client.post(
                    f"{telegram_api_url}/sendVideo",
                    json=data
                )

            else:
                # Обычное текстовое сообщение
                data = {
                    "chat_id": user_id,
                    "text": text,
                    "parse_mode": "HTML",
                }
                if reply_markup:
                    data["reply_markup"] = reply_markup

                response = await client.post(
                    f"{telegram_api_url}/sendMessage",
                    json=data
                )

            result = response.json()

            if result.get("ok"):
                return True, None
            else:
                error = result.get("description", "Unknown error")
                return False, error

    except httpx.RequestError as e:
        return False, f"HTTP error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


async def add_gift_images_to_user(user_id: int, amount: int) -> bool:
    """Начислить бонусные изображения пользователю"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ImageBalance).where(ImageBalance.user_id == user_id)
            )
            balance = result.scalar_one_or_none()

            if balance:
                balance.total_purchased_images += amount
                balance.remaining_purchased_images += amount
            else:
                balance = ImageBalance(
                    user_id=user_id,
                    total_purchased_images=amount,
                    remaining_purchased_images=amount,
                    daily_subscription_quota=0,
                    daily_subscription_used=0
                )
                db.add(balance)

            await db.commit()
            logger.info(f"Added {amount} gift images to user {user_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to add gift images to user {user_id}: {e}")
        return False


async def _execute_scheduled_broadcast_async(broadcast_id: int) -> Dict[str, Any]:
    """
    Выполнить запланированную рассылку всем активным пользователям
    """
    logger.info(f"Starting scheduled broadcast {broadcast_id}")

    try:
        async with AsyncSessionLocal() as db:
            # Получить рассылку
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                logger.error(f"Broadcast {broadcast_id} not found")
                return {"status": "error", "message": "Broadcast not found"}

            if broadcast.status == BroadcastStatus.CANCELLED:
                logger.info(f"Broadcast {broadcast_id} was cancelled, skipping")
                return {"status": "cancelled"}

            # Обновить статус на running
            broadcast.status = BroadcastStatus.RUNNING
            broadcast.started_at = datetime.utcnow()
            await db.commit()

            # Получить всех активных пользователей
            users_result = await db.execute(
                select(User.id).where(
                    and_(User.is_active == True, User.is_blocked == False)
                )
            )
            user_ids = [row[0] for row in users_result.fetchall()]

            broadcast.total_recipients = len(user_ids)
            await db.commit()

            logger.info(f"Broadcast {broadcast_id}: sending to {len(user_ids)} users")

            sent_count = 0
            failed_count = 0

            # Отправка сообщений
            for user_id in user_ids:
                # Проверить отмену
                await db.refresh(broadcast)
                if broadcast.status == BroadcastStatus.CANCELLED:
                    logger.info(f"Broadcast {broadcast_id} cancelled during execution")
                    break

                # Отправить сообщение
                success, error = await send_broadcast_message(
                    user_id=user_id,
                    text=broadcast.text,
                    media_url=broadcast.media_url,
                    media_type=broadcast.media_type,
                    buttons=broadcast.buttons,
                )

                # Записать лог
                log = BroadcastLog(
                    broadcast_id=broadcast_id,
                    user_id=user_id,
                    success=success,
                    error_message=error
                )
                db.add(log)

                if success:
                    sent_count += 1

                    # Начислить изображения если есть
                    if broadcast.gift_images > 0:
                        await add_gift_images_to_user(user_id, broadcast.gift_images)
                else:
                    failed_count += 1

                # Обновить счетчики каждые 10 сообщений
                if (sent_count + failed_count) % 10 == 0:
                    broadcast.sent_count = sent_count
                    broadcast.failed_count = failed_count
                    await db.commit()

                # Небольшая задержка чтобы не превысить rate limit
                await asyncio.sleep(0.05)

            # Финальное обновление
            broadcast.sent_count = sent_count
            broadcast.failed_count = failed_count
            broadcast.status = BroadcastStatus.COMPLETED
            broadcast.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Broadcast {broadcast_id} completed: sent={sent_count}, failed={failed_count}")

            return {
                "status": "completed",
                "broadcast_id": broadcast_id,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_recipients": len(user_ids)
            }

    except Exception as e:
        logger.error(f"Broadcast {broadcast_id} failed: {e}", exc_info=True)

        # Обновить статус на failed
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Broadcast).where(Broadcast.id == broadcast_id)
                )
                broadcast = result.scalar_one_or_none()
                if broadcast:
                    broadcast.status = BroadcastStatus.FAILED
                    await db.commit()
        except:
            pass

        return {"status": "error", "message": str(e)}


async def _send_new_user_broadcast_async(user_id: int, broadcast_id: int) -> Dict[str, Any]:
    """
    Отправить рассылку новому пользователю
    """
    logger.info(f"Sending new user broadcast {broadcast_id} to user {user_id}")

    try:
        async with AsyncSessionLocal() as db:
            # Получить рассылку
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                return {"status": "error", "message": "Broadcast not found"}

            if broadcast.status != BroadcastStatus.SCHEDULED:
                return {"status": "skipped", "message": "Broadcast not active"}

            # Проверить что пользователь еще не получал эту рассылку
            existing_log = await db.execute(
                select(BroadcastLog).where(
                    and_(
                        BroadcastLog.broadcast_id == broadcast_id,
                        BroadcastLog.user_id == user_id
                    )
                )
            )
            if existing_log.scalar_one_or_none():
                return {"status": "skipped", "message": "Already sent to this user"}

            # Отправить сообщение
            success, error = await send_broadcast_message(
                user_id=user_id,
                text=broadcast.text,
                media_url=broadcast.media_url,
                media_type=broadcast.media_type,
                buttons=broadcast.buttons,
            )

            # Записать лог
            log = BroadcastLog(
                broadcast_id=broadcast_id,
                user_id=user_id,
                success=success,
                error_message=error
            )
            db.add(log)

            # Обновить счетчики
            broadcast.total_recipients += 1
            if success:
                broadcast.sent_count += 1

                # Начислить изображения если есть
                if broadcast.gift_images > 0:
                    await add_gift_images_to_user(user_id, broadcast.gift_images)
            else:
                broadcast.failed_count += 1

            await db.commit()

            return {
                "status": "completed" if success else "failed",
                "user_id": user_id,
                "broadcast_id": broadcast_id,
                "error": error
            }

    except Exception as e:
        logger.error(f"New user broadcast failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def _check_new_user_broadcasts_async() -> Dict[str, Any]:
    """
    Проверить и отправить рассылки новым пользователям
    Вызывается периодически (каждые 5 минут)
    """
    logger.info("Checking new user broadcasts")

    try:
        async with AsyncSessionLocal() as db:
            # Получить активные рассылки для новых пользователей
            broadcasts_result = await db.execute(
                select(Broadcast).where(
                    and_(
                        Broadcast.broadcast_type == BroadcastType.NEW_USER,
                        Broadcast.status == BroadcastStatus.SCHEDULED
                    )
                )
            )
            broadcasts = broadcasts_result.scalars().all()

            if not broadcasts:
                return {"status": "ok", "message": "No active new user broadcasts"}

            sent_count = 0

            for broadcast in broadcasts:
                delay_minutes = broadcast.delay_minutes or 30

                # Найти пользователей, зарегистрированных delay_minutes назад (с допуском 5 минут)
                target_time = datetime.utcnow() - timedelta(minutes=delay_minutes)
                window_start = target_time - timedelta(minutes=5)
                window_end = target_time + timedelta(minutes=5)

                # Получить пользователей в этом временном окне, которым еще не отправлялась эта рассылка
                users_result = await db.execute(
                    select(User.id).where(
                        and_(
                            User.is_active == True,
                            User.is_blocked == False,
                            User.created_at >= window_start,
                            User.created_at <= window_end,
                            ~User.id.in_(
                                select(BroadcastLog.user_id).where(
                                    BroadcastLog.broadcast_id == broadcast.id
                                )
                            )
                        )
                    )
                )
                user_ids = [row[0] for row in users_result.fetchall()]

                for user_id in user_ids:
                    result = await _send_new_user_broadcast_async(user_id, broadcast.id)
                    if result.get("status") == "completed":
                        sent_count += 1

                    await asyncio.sleep(0.05)

            return {
                "status": "ok",
                "broadcasts_checked": len(broadcasts),
                "messages_sent": sent_count
            }

    except Exception as e:
        logger.error(f"Check new user broadcasts failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ==================== CELERY TASKS ====================

@celery_app.task(name="broadcast.execute_scheduled_broadcast", bind=True, max_retries=3)
def execute_scheduled_broadcast(self, broadcast_id: int):
    """
    Выполнить запланированную рассылку (Celery task wrapper)
    """
    try:
        logger.info(f"Executing scheduled broadcast task for broadcast {broadcast_id}")
        result = asyncio.run(_execute_scheduled_broadcast_async(broadcast_id))
        return result
    except Exception as e:
        logger.error(f"Scheduled broadcast task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="broadcast.send_new_user_broadcast", bind=True, max_retries=3)
def send_new_user_broadcast(self, user_id: int, broadcast_id: int):
    """
    Отправить рассылку новому пользователю (Celery task wrapper)
    """
    try:
        logger.info(f"Sending new user broadcast {broadcast_id} to user {user_id}")
        result = asyncio.run(_send_new_user_broadcast_async(user_id, broadcast_id))
        return result
    except Exception as e:
        logger.error(f"New user broadcast task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="broadcast.check_new_user_broadcasts", bind=True, max_retries=3)
def check_new_user_broadcasts(self):
    """
    Проверить и отправить рассылки новым пользователям (Celery task wrapper)
    Запускается каждые 5 минут через Celery Beat
    """
    try:
        logger.info("Running check new user broadcasts task")
        result = asyncio.run(_check_new_user_broadcasts_async())
        return result
    except Exception as e:
        logger.error(f"Check new user broadcasts task failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
