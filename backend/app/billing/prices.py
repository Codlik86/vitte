from __future__ import annotations

from dataclasses import dataclass


# Stars расчёт: заданные цены (руб) конвертируем с запасом.
# Дано: 250⭐ ≈ 529₽ (айфон). Берём 1⭐ ≈ 2.1₽ с запасом (~12% буфер).
RUB_PER_STAR = 2.1


@dataclass(frozen=True)
class PlanPrice:
    code: str
    title: str
    price_rub: int

    @property
    def price_stars(self) -> int:
        return max(1, round(self.price_rub / RUB_PER_STAR))


SUBSCRIPTION_PLANS: dict[str, PlanPrice] = {
    "sub_3d": PlanPrice(code="sub_3d", title="3 дня", price_rub=299),
    "sub_week": PlanPrice(code="sub_week", title="1 неделя", price_rub=599),
    "sub_month": PlanPrice(code="sub_month", title="1 месяц", price_rub=999),
    "sub_quarter": PlanPrice(code="sub_quarter", title="3 месяца", price_rub=2199),
}


FEATURE_PRICES_STARS: dict[str, int] = {
    "long_letters_month": 150,
    "voice_month": 300,
    "deep_mode_month": 300,
    "fantasy_pack_month": 300,
}
