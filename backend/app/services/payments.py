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
    period: Literal["day", "week", "month", "quarter", "year"]
    provider: str = "yookassa"
    recommended: bool = False


PAYMENT_PLANS: List[PaymentPlan] = [
    PaymentPlan(
        code="premium_3d",
        title="3 дня Premium",
        description="Познакомься с безлимитом и улучшенными ответами на 3 дня.",
        price=299,
        currency="RUB",
        period="day",
    ),
    PaymentPlan(
        code="premium_1w",
        title="Неделя Premium",
        description="Безлимит и глубокие сцены на 7 дней.",
        price=599,
        currency="RUB",
        period="week",
    ),
    PaymentPlan(
        code="premium_1m",
        title="Месяц Premium",
        description="Безлимитные сообщения и продвинутые эмоции на 30 дней.",
        price=999,
        currency="RUB",
        period="month",
        recommended=True,
    ),
    PaymentPlan(
        code="premium_3m",
        title="3 месяца Premium",
        description="Экономия и длинные истории без ограничений.",
        price=2199,
        currency="RUB",
        period="quarter",
    ),
]


def list_payment_plans() -> List[PaymentPlan]:
    return PAYMENT_PLANS


def get_payment_plan(plan_code: str) -> PaymentPlan | None:
    return next((plan for plan in PAYMENT_PLANS if plan.code == plan_code), None)


def estimate_valid_until(plan: PaymentPlan, started_at: datetime | None = None) -> datetime:
    started = started_at or datetime.utcnow()
    if plan.period == "day":
        delta = timedelta(days=3)
    elif plan.period == "week":
        delta = timedelta(days=7)
    elif plan.period == "month":
        delta = timedelta(days=30)
    elif plan.period == "quarter":
        delta = timedelta(days=90)
    else:
        delta = timedelta(days=365)
    return started + delta
