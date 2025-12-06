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
    "plus_2d": PlanPrice(code="plus_2d", title="2 дня", price_rub=int(199 * RUB_PER_STAR)),
    "plus_7d": PlanPrice(code="plus_7d", title="7 дней", price_rub=int(399 * RUB_PER_STAR)),
    "plus_30d": PlanPrice(code="plus_30d", title="30 дней", price_rub=int(999 * RUB_PER_STAR)),
}


FEATURE_PRICES_STARS: dict[str, int] = {
    "intense_mode": 150,
    "fantasy_scenes": 200,
}
