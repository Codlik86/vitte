from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StoreProduct:
    product_code: str
    title: str
    description: str
    price_stars: int
    type: str


STORE_PRODUCTS: List[StoreProduct] = [
    StoreProduct(
        product_code="long_letters_month",
        title="Большие письма",
        description="Длинные и тёплые ответы в 3–5 раз больше обычного.",
        price_stars=150,
        type="feature",
    ),
    StoreProduct(
        product_code="voice_month",
        title="Голос персонажа",
        description="Персонаж будет отвечать голосовыми сообщениями.",
        price_stars=300,
        type="feature",
    ),
    StoreProduct(
        product_code="deep_mode_month",
        title="Глубокие отношения",
        description="Больше эмоциональности, искренности и романтики.",
        price_stars=300,
        type="feature",
    ),
    StoreProduct(
        product_code="fantasy_pack_month",
        title="Фантазии и образы",
        description="Визуальные сцены и образы (функция скоро будет доступна).",
        price_stars=300,
        type="feature",
    ),
]


def list_store_products() -> List[StoreProduct]:
    return STORE_PRODUCTS


def get_store_product(product_code: str) -> StoreProduct | None:
    return next((p for p in STORE_PRODUCTS if p.product_code == product_code), None)
