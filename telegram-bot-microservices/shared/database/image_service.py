"""
Image Balance Service - управление квотой изображений

Логика:
- Free: 3 изображения разово (remaining_purchased_images)
- Premium: безлимитная генерация (daily_subscription_quota > 0 = признак подписки)
"""

from datetime import datetime, timezone
from typing import Optional
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

    # Если флаг подписки выставлен — проверяем актуальность подписки
    if image_balance.daily_subscription_quota > 0:
        now = datetime.now(timezone.utc)
        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = sub_result.scalar_one_or_none()
        sub_active = (
            subscription is not None
            and subscription.is_active
            and subscription.expires_at is not None
            and subscription.expires_at > now
        )
        if not sub_active:
            # Подписка истекла — сбрасываем флаг
            image_balance.daily_subscription_quota = 0

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

    remaining_purchased = image_balance.remaining_purchased_images
    return ImageQuotaResult(
        can_generate=remaining_purchased > 0,
        remaining_daily=0,
        remaining_purchased=remaining_purchased,
        total_remaining=remaining_purchased
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

    remaining_purchased = image_balance.remaining_purchased_images

    if remaining_purchased <= 0:
        return ImageQuotaResult(
            can_generate=False,
            remaining_daily=0,
            remaining_purchased=0,
            total_remaining=0,
            error="Лимит изображений исчерпан"
        )

    image_balance.remaining_purchased_images -= 1
    await db.flush()

    remaining = image_balance.remaining_purchased_images
    return ImageQuotaResult(
        can_generate=True,
        remaining_daily=0,
        remaining_purchased=remaining,
        total_remaining=remaining,
        source="purchased"
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
