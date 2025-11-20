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
        product_code="deep_mode",
        title="Deep Mode",
        description="Глубокая эмоциональная проработка и более чувственные диалоги.",
        price_stars=120,
        type="one_time",
    ),
    StoreProduct(
        product_code="long_letter",
        title="Long Letters",
        description="Длинные романтические письма и признания.",
        price_stars=160,
        type="one_time",
    ),
    StoreProduct(
        product_code="episode_memory",
        title="Episodes",
        description="Платные эпизоды вашей истории с сохранёнными сценами.",
        price_stars=200,
        type="episode",
    ),
    StoreProduct(
        product_code="cosmetic_pack_neon",
        title="Cosmetic Pack",
        description="Темы, эмоции и косметические настройки без NSFW-контента.",
        price_stars=90,
        type="cosmetic",
    ),
]


def list_store_products() -> List[StoreProduct]:
    return STORE_PRODUCTS


def get_store_product(product_code: str) -> StoreProduct | None:
    return next((p for p in STORE_PRODUCTS if p.product_code == product_code), None)
