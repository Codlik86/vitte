"""
Broadcast management routes for admin panel
"""
import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func, and_

from shared.database import (
    get_db,
    User,
    Broadcast,
    BroadcastLog,
    BroadcastType,
    BroadcastStatus,
    ImageBalance,
)
from shared.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/broadcast", tags=["broadcast"])

# MinIO/S3 настройки
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "broadcasts")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "https://vitteapp.duckdns.org")


# ==================== SCHEMAS ====================

class ButtonSchema(BaseModel):
    """Схема кнопки для рассылки"""
    text: str
    callback_data: str


class CreateBroadcastRequest(BaseModel):
    """Запрос на создание рассылки"""
    name: str
    broadcast_type: str  # "new_user" или "scheduled"
    text: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # "photo" или "video"
    buttons: Optional[List[ButtonSchema]] = None
    gift_images: Optional[int] = 0
    delay_minutes: Optional[int] = None  # Для new_user: 30, 60, 120, 180
    scheduled_at: Optional[str] = None  # ISO format для scheduled


class UpdateBroadcastRequest(BaseModel):
    """Запрос на обновление рассылки"""
    name: Optional[str] = None
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    buttons: Optional[List[ButtonSchema]] = None
    gift_images: Optional[int] = None
    delay_minutes: Optional[int] = None
    scheduled_at: Optional[str] = None


class BroadcastResponse(BaseModel):
    """Ответ с данными рассылки"""
    id: int
    name: str
    broadcast_type: str
    status: str
    text: str
    media_url: Optional[str]
    media_type: Optional[str]
    buttons: Optional[List[dict]]
    gift_images: int
    delay_minutes: Optional[int]
    scheduled_at: Optional[str]
    total_recipients: int
    sent_count: int
    failed_count: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress_percent: float

    class Config:
        from_attributes = True


# ==================== HELPERS ====================

def broadcast_to_response(b: Broadcast) -> dict:
    """Конвертация модели Broadcast в response dict"""
    progress = 0.0
    if b.total_recipients > 0:
        progress = round((b.sent_count + b.failed_count) / b.total_recipients * 100, 1)

    return {
        "id": b.id,
        "name": b.name,
        "broadcast_type": b.broadcast_type,
        "status": b.status,
        "text": b.text,
        "media_url": b.media_url,
        "media_type": b.media_type,
        "buttons": b.buttons,
        "gift_images": b.gift_images or 0,
        "delay_minutes": b.delay_minutes,
        "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
        "total_recipients": b.total_recipients or 0,
        "sent_count": b.sent_count or 0,
        "failed_count": b.failed_count or 0,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "progress_percent": progress,
    }


# ==================== ENDPOINTS ====================

@router.get("/list")
async def list_broadcasts(
    status: Optional[str] = None,
    broadcast_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Получить список рассылок с фильтрацией

    - status: draft, scheduled, running, completed, cancelled, failed
    - broadcast_type: new_user, scheduled
    """
    try:
        async for db in get_db():
            query = select(Broadcast).order_by(Broadcast.created_at.desc())

            if status:
                query = query.where(Broadcast.status == status)
            if broadcast_type:
                query = query.where(Broadcast.broadcast_type == broadcast_type)

            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            broadcasts = result.scalars().all()

            return [broadcast_to_response(b) for b in broadcasts]

    except Exception as e:
        logger.error(f"Error listing broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_broadcasts():
    """
    Получить активные рассылки (running и scheduled) для мониторинга
    """
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast)
                .where(Broadcast.status.in_([
                    BroadcastStatus.RUNNING,
                    BroadcastStatus.SCHEDULED
                ]))
                .order_by(Broadcast.created_at.desc())
            )
            broadcasts = result.scalars().all()

            return [broadcast_to_response(b) for b in broadcasts]

    except Exception as e:
        logger.error(f"Error getting active broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{broadcast_id}")
async def get_broadcast(broadcast_id: int):
    """Получить рассылку по ID"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            return broadcast_to_response(broadcast)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_broadcast(request: CreateBroadcastRequest):
    """Создать новую рассылку"""
    try:
        # Валидация типа
        if request.broadcast_type not in ["new_user", "scheduled"]:
            raise HTTPException(status_code=400, detail="Invalid broadcast_type")

        # Валидация для new_user
        if request.broadcast_type == "new_user":
            if not request.delay_minutes:
                raise HTTPException(status_code=400, detail="delay_minutes required for new_user type")
            if request.delay_minutes not in [30, 60, 120, 180]:
                raise HTTPException(status_code=400, detail="delay_minutes must be 30, 60, 120 or 180")

        # Валидация для scheduled
        if request.broadcast_type == "scheduled":
            if not request.scheduled_at:
                raise HTTPException(status_code=400, detail="scheduled_at required for scheduled type")

        async for db in get_db():
            # Подготовка кнопок
            buttons_data = None
            if request.buttons:
                buttons_data = [{"text": b.text, "callback_data": b.callback_data} for b in request.buttons]

            # Парсинг даты для scheduled
            scheduled_at = None
            if request.scheduled_at:
                scheduled_at = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))

            broadcast = Broadcast(
                name=request.name,
                broadcast_type=request.broadcast_type,
                status=BroadcastStatus.DRAFT,
                text=request.text,
                media_url=request.media_url,
                media_type=request.media_type,
                buttons=buttons_data,
                gift_images=request.gift_images or 0,
                delay_minutes=request.delay_minutes,
                scheduled_at=scheduled_at,
            )

            db.add(broadcast)
            await db.commit()
            await db.refresh(broadcast)

            logger.info(f"Created broadcast {broadcast.id}: {broadcast.name}")

            return broadcast_to_response(broadcast)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{broadcast_id}")
async def update_broadcast(broadcast_id: int, request: UpdateBroadcastRequest):
    """Обновить рассылку (только draft)"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            if broadcast.status != BroadcastStatus.DRAFT:
                raise HTTPException(status_code=400, detail="Can only edit draft broadcasts")

            # Обновление полей
            if request.name is not None:
                broadcast.name = request.name
            if request.text is not None:
                broadcast.text = request.text
            if request.media_url is not None:
                broadcast.media_url = request.media_url
            if request.media_type is not None:
                broadcast.media_type = request.media_type
            if request.buttons is not None:
                broadcast.buttons = [{"text": b.text, "callback_data": b.callback_data} for b in request.buttons]
            if request.gift_images is not None:
                broadcast.gift_images = request.gift_images
            if request.delay_minutes is not None:
                broadcast.delay_minutes = request.delay_minutes
            if request.scheduled_at is not None:
                broadcast.scheduled_at = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))

            await db.commit()
            await db.refresh(broadcast)

            logger.info(f"Updated broadcast {broadcast_id}")

            return broadcast_to_response(broadcast)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{broadcast_id}/schedule")
async def schedule_broadcast(broadcast_id: int):
    """
    Запланировать рассылку (перевести из draft в scheduled)
    Для scheduled типа - запускает Celery задачу на указанное время
    Для new_user типа - активирует правило для новых пользователей
    """
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            if broadcast.status != BroadcastStatus.DRAFT:
                raise HTTPException(status_code=400, detail="Can only schedule draft broadcasts")

            # Подсчет получателей
            if broadcast.broadcast_type == BroadcastType.SCHEDULED:
                # Для scheduled - все активные пользователи
                count_result = await db.execute(
                    select(func.count(User.id)).where(
                        and_(User.is_active == True, User.is_blocked == False)
                    )
                )
                total_recipients = count_result.scalar() or 0

                # Запуск Celery задачи
                from app.utils.celery_client import schedule_broadcast_task
                task_id = await schedule_broadcast_task(broadcast_id, broadcast.scheduled_at)
                broadcast.celery_task_id = task_id

            else:
                # Для new_user - пока 0, будет увеличиваться при регистрациях
                total_recipients = 0

            broadcast.status = BroadcastStatus.SCHEDULED
            broadcast.total_recipients = total_recipients

            await db.commit()
            await db.refresh(broadcast)

            logger.info(f"Scheduled broadcast {broadcast_id}, recipients: {total_recipients}")

            return broadcast_to_response(broadcast)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{broadcast_id}/cancel")
async def cancel_broadcast(broadcast_id: int):
    """Отменить рассылку"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            if broadcast.status not in [BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED, BroadcastStatus.RUNNING]:
                raise HTTPException(status_code=400, detail="Cannot cancel this broadcast")

            # Отмена Celery задачи если есть
            if broadcast.celery_task_id:
                from app.utils.celery_client import cancel_broadcast_task
                await cancel_broadcast_task(broadcast.celery_task_id)

            broadcast.status = BroadcastStatus.CANCELLED

            await db.commit()
            await db.refresh(broadcast)

            logger.info(f"Cancelled broadcast {broadcast_id}")

            return broadcast_to_response(broadcast)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{broadcast_id}")
async def delete_broadcast(broadcast_id: int):
    """Удалить рассылку (только draft или cancelled)"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            if broadcast.status not in [BroadcastStatus.DRAFT, BroadcastStatus.CANCELLED]:
                raise HTTPException(status_code=400, detail="Can only delete draft or cancelled broadcasts")

            await db.delete(broadcast)
            await db.commit()

            logger.info(f"Deleted broadcast {broadcast_id}")

            return {"success": True, "message": "Broadcast deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{broadcast_id}/stats")
async def get_broadcast_stats(broadcast_id: int):
    """Получить детальную статистику рассылки"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                raise HTTPException(status_code=404, detail="Broadcast not found")

            # Статистика из логов
            success_count = await db.execute(
                select(func.count(BroadcastLog.id))
                .where(and_(
                    BroadcastLog.broadcast_id == broadcast_id,
                    BroadcastLog.success == True
                ))
            )

            failed_count = await db.execute(
                select(func.count(BroadcastLog.id))
                .where(and_(
                    BroadcastLog.broadcast_id == broadcast_id,
                    BroadcastLog.success == False
                ))
            )

            # Последние ошибки
            errors_result = await db.execute(
                select(BroadcastLog)
                .where(and_(
                    BroadcastLog.broadcast_id == broadcast_id,
                    BroadcastLog.success == False
                ))
                .order_by(BroadcastLog.sent_at.desc())
                .limit(10)
            )
            recent_errors = errors_result.scalars().all()

            return {
                "broadcast": broadcast_to_response(broadcast),
                "stats": {
                    "success_count": success_count.scalar() or 0,
                    "failed_count": failed_count.scalar() or 0,
                    "pending_count": max(0, broadcast.total_recipients - broadcast.sent_count - broadcast.failed_count),
                },
                "recent_errors": [
                    {
                        "user_id": log.user_id,
                        "error": log.error_message,
                        "sent_at": log.sent_at.isoformat() if log.sent_at else None
                    }
                    for log in recent_errors
                ]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting broadcast stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/new-user/active")
async def get_active_new_user_broadcasts():
    """Получить активные рассылки для новых пользователей"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(Broadcast)
                .where(and_(
                    Broadcast.broadcast_type == BroadcastType.NEW_USER,
                    Broadcast.status == BroadcastStatus.SCHEDULED
                ))
                .order_by(Broadcast.delay_minutes)
            )
            broadcasts = result.scalars().all()

            return [broadcast_to_response(b) for b in broadcasts]

    except Exception as e:
        logger.error(f"Error getting active new user broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузить медиа-файл (фото/видео) для рассылки
    Сохраняет файл в БД и возвращает URL для получения
    """
    try:
        from shared.database.models import BroadcastMedia

        # Проверка типа файла
        content_type = file.content_type or ""
        if not content_type.startswith(("image/", "video/")):
            raise HTTPException(status_code=400, detail="Only image and video files allowed")

        # Читаем файл
        contents = await file.read()
        file_size = len(contents)

        # Проверяем размер (макс 20MB для фото, 50MB для видео)
        is_video = content_type.startswith("video/")
        max_size = 50 * 1024 * 1024 if is_video else 20 * 1024 * 1024

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {max_size // (1024*1024)}MB"
            )

        # Определяем тип медиа
        media_type = "photo" if content_type.startswith("image/") else "video"

        # Генерируем уникальный ID
        file_id = uuid.uuid4().hex

        # Сохраняем в БД
        media = BroadcastMedia(
            id=file_id,
            file_data=contents,
            content_type=content_type,
            file_size=file_size,
            media_type=media_type
        )

        db.add(media)
        await db.commit()

        # Формируем URL для получения файла
        public_url = f"{MINIO_PUBLIC_URL}/api/broadcast/media/{file_id}"

        logger.info(f"Uploaded media to DB: id={file_id}, size={file_size}, type={media_type}")

        return {
            "success": True,
            "url": public_url,
            "media_type": media_type,
            "filename": file.filename,
            "size": file_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/{file_id}")
async def get_media(file_id: str, db = Depends(get_db)):
    """
    Получить медиа файл по ID
    """
    from shared.database.models import BroadcastMedia
    from sqlalchemy import select

    try:
        # Получаем файл из БД
        result = await db.execute(
            select(BroadcastMedia).where(BroadcastMedia.id == file_id)
        )
        media = result.scalar_one_or_none()

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Возвращаем файл с правильным content-type
        return Response(
            content=media.file_data,
            media_type=media.content_type,
            headers={
                "Cache-Control": "public, max-age=604800",  # 7 days
                "Content-Length": str(media.file_size)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media: {e}")
        raise HTTPException(status_code=500, detail=str(e))
