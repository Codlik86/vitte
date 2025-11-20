from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Literal


@dataclass(frozen=True)
class PaymentPlan:
    code: str
    title: str
    description: str
    price: int
    currency: str
    period: Literal["week", "month", "quarter", "year"]
    provider: str = "yookassa"
    recommended: bool = False


PAYMENT_PLANS: List[PaymentPlan] = [
    PaymentPlan(
        code="premium_week",
        title="Неделя Premium",
        description="Попробуй безлимит и улучшенные сцены на 7 дней.",
        price=399,
        currency="RUB",
        period="week",
    ),
    PaymentPlan(
        code="premium_month",
        title="Месяц Premium",
        description="Безлимитные сообщения и продвинутые эмоции на 30 дней.",
        price=999,
        currency="RUB",
        period="month",
        recommended=True,
    ),
    PaymentPlan(
        code="premium_quarter",
        title="Квартал Premium",
        description="Экономия и длинные истории без ограничений.",
        price=2390,
        currency="RUB",
        period="quarter",
    ),
    PaymentPlan(
        code="premium_year",
        title="Год Premium",
        description="Максимальный срок и лучшие условия.",
        price=7990,
        currency="RUB",
        period="year",
    ),
]


def list_payment_plans() -> List[PaymentPlan]:
    return PAYMENT_PLANS


def get_payment_plan(plan_code: str) -> PaymentPlan | None:
    return next((plan for plan in PAYMENT_PLANS if plan.code == plan_code), None)


def estimate_valid_until(plan: PaymentPlan, started_at: datetime | None = None) -> datetime:
    started = started_at or datetime.utcnow()
    if plan.period == "week":
        delta = timedelta(days=7)
    elif plan.period == "month":
        delta = timedelta(days=30)
    elif plan.period == "quarter":
        delta = timedelta(days=90)
    else:
        delta = timedelta(days=365)
    return started + delta
