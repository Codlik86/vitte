"""
Image Balance Service - управление квотой изображений

Логика:
- Free: 10 изображений разово (remaining_purchased_images)
- Premium: 20 изображений в день (daily_subscription_quota)
- При новом дне: daily_subscription_used сбрасывается до 0 (НЕ накапливается!)
- Сначала тратятся ежедневные, потом купленные
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import ImageBalance, Subscription


@dataclass
class ImageQuotaResult:
    """Результат проверки квоты изображений."""
    can_generate: bool
    remaining_daily: int  # Осталось из ежедневной квоты Premium
    remaining_purchased: int  # Осталось из купленных
    total_remaining: int  # Всего осталось
    source: Optional[str] = None  # "daily" или "purchased" - откуда списали
    error: Optional[str] = None


async def check_and_reset_daily_quota(
    db: AsyncSession,
    user_id: int
) -> Optional[ImageBalance]:
    """
    Проверить и сбросить ежедневную квоту если новый день.

    ВАЖНО: Квота НЕ накапливается!
    Если вчера осталось 10 из 20, сегодня будет снова 20, а не 30.

    Returns:
        ImageBalance или None если не найден
    """
    result = await db.execute(
        select(ImageBalance).where(ImageBalance.user_id == user_id)
    )
    image_balance = result.scalar_one_or_none()

    if not image_balance:
        return None

    # Проверяем нужен ли сброс ежедневной квоты
    today = datetime.now(timezone.utc).date()

    if image_balance.daily_quota_date is None:
        # Первый раз - устанавливаем дату
        image_balance.daily_quota_date = datetime.now(timezone.utc)
        image_balance.daily_subscription_used = 0
    elif image_balance.daily_quota_date.date() != today:
        # Новый день - СБРАСЫВАЕМ счётчик использованных (не добавляем!)
        image_balance.daily_subscription_used = 0
        image_balance.daily_quota_date = datetime.now(timezone.utc)

    await db.flush()
    return image_balance


async def get_images_remaining(
    db: AsyncSession,
    user_id: int
) -> ImageQuotaResult:
    """
    Получить количество оставшихся изображений.
    Автоматически сбрасывает ежедневную квоту если новый день.

    Returns:
        ImageQuotaResult с информацией о квоте
    """
    # Проверяем и сбрасываем квоту если нужно
    image_balance = await check_and_reset_daily_quota(db, user_id)

    if not image_balance:
        return ImageQuotaResult(
            can_generate=False,
            remaining_daily=0,
            remaining_purchased=0,
            total_remaining=0,
            error="Баланс изображений не найден"
        )

    # Считаем остатки
    remaining_daily = max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used)
    remaining_purchased = image_balance.remaining_purchased_images
    total = remaining_daily + remaining_purchased

    return ImageQuotaResult(
        can_generate=total > 0,
        remaining_daily=remaining_daily,
        remaining_purchased=remaining_purchased,
        total_remaining=total
    )


async def use_image_quota(
    db: AsyncSession,
    user_id: int
) -> ImageQuotaResult:
    """
    Использовать 1 изображение из квоты.

    Приоритет списания:
    1. Сначала из ежедневной квоты Premium (daily)
    2. Потом из купленных (purchased)

    Returns:
        ImageQuotaResult с обновлённой информацией
    """
    # Проверяем и сбрасываем квоту если нужно
    image_balance = await check_and_reset_daily_quota(db, user_id)

    if not image_balance:
        return ImageQuotaResult(
            can_generate=False,
            remaining_daily=0,
            remaining_purchased=0,
            total_remaining=0,
            error="Баланс изображений не найден"
        )

    # Считаем текущие остатки
    remaining_daily = max(0, image_balance.daily_subscription_quota - image_balance.daily_subscription_used)
    remaining_purchased = image_balance.remaining_purchased_images

    source = None

    # Списываем в порядке приоритета
    if remaining_daily > 0:
        # Есть ежедневная квота - списываем оттуда
        image_balance.daily_subscription_used += 1
        remaining_daily -= 1
        source = "daily"
    elif remaining_purchased > 0:
        # Ежедневная кончилась - списываем из купленных
        image_balance.remaining_purchased_images -= 1
        remaining_purchased -= 1
        source = "purchased"
    else:
        # Нет доступных изображений
        return ImageQuotaResult(
            can_generate=False,
            remaining_daily=0,
            remaining_purchased=0,
            total_remaining=0,
            error="Лимит изображений исчерпан"
        )

    await db.flush()

    return ImageQuotaResult(
        can_generate=True,
        remaining_daily=remaining_daily,
        remaining_purchased=remaining_purchased,
        total_remaining=remaining_daily + remaining_purchased,
        source=source
    )


async def add_purchased_images(
    db: AsyncSession,
    user_id: int,
    count: int
) -> ImageQuotaResult:
    """
    Добавить купленные изображения к балансу.

    Args:
        user_id: ID пользователя
        count: Количество изображений для добавления

    Returns:
        ImageQuotaResult с обновлённой информацией
    """
    result = await db.execute(
        select(ImageBalance).where(ImageBalance.user_id == user_id)
    )
    image_balance = result.scalar_one_or_none()

    if not image_balance:
        # Создаём новый баланс
        image_balance = ImageBalance(
            user_id=user_id,
            total_purchased_images=count,
            remaining_purchased_images=count,
            daily_subscription_quota=0,
            daily_subscription_used=0
        )
        db.add(image_balance)
    else:
        # Добавляем к существующему
        image_balance.total_purchased_images += count
        image_balance.remaining_purchased_images += count

    await db.flush()

    # Получаем актуальные остатки
    return await get_images_remaining(db, user_id)


__all__ = [
    "ImageQuotaResult",
    "check_and_reset_daily_quota",
    "get_images_remaining",
    "use_image_quota",
    "add_purchased_images",
]
