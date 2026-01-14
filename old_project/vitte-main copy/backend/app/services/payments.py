from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from ..services.store import SUBSCRIPTION_PLANS, get_plan


def list_payment_plans() -> List:
    return SUBSCRIPTION_PLANS


def get_payment_plan(plan_code: str):
    return get_plan(plan_code)


def estimate_valid_until(plan, started_at: datetime | None = None) -> datetime:
    started = started_at or datetime.utcnow()
    return started + timedelta(days=plan.duration_days)
