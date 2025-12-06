from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SubscriptionPlan:
    code: str
    title: str
    description: str
    duration_days: int
    price_stars: int
    is_most_popular: bool = False


@dataclass(frozen=True)
class ImagePack:
    code: str
    images: int
    price_stars: int


@dataclass(frozen=True)
class EmotionalFeature:
    code: str
    title: str
    description: str
    price_stars: int


SUBSCRIPTION_PLANS: List[SubscriptionPlan] = [
    SubscriptionPlan(code="plus_2d", title="Vitte Plus 2 дня", description="Безлимит сообщений + 20 изображений/день", duration_days=2, price_stars=199),
    SubscriptionPlan(code="plus_7d", title="Vitte Plus 7 дней", description="Безлимит сообщений + 20 изображений/день", duration_days=7, price_stars=399, is_most_popular=True),
    SubscriptionPlan(code="plus_30d", title="Vitte Plus 30 дней", description="Безлимит сообщений + 20 изображений/день", duration_days=30, price_stars=999),
]

IMAGE_PACKS: List[ImagePack] = [
    ImagePack(code="IMAGE_PACK_20", images=20, price_stars=50),
    ImagePack(code="IMAGE_PACK_50", images=50, price_stars=120),
    ImagePack(code="IMAGE_PACK_100", images=100, price_stars=250),
    ImagePack(code="IMAGE_PACK_200", images=200, price_stars=500),
]

EMOTIONAL_FEATURES: List[EmotionalFeature] = [
    EmotionalFeature(code="intense_mode", title="Режим страсти", description="Более чувственное общение при достаточном доверии.", price_stars=150),
    EmotionalFeature(code="fantasy_scenes", title="Фантазии и сцены", description="Доступ к особым сценариям и фантазиям.", price_stars=200),
]


def get_plan(code: str) -> SubscriptionPlan | None:
    return next((p for p in SUBSCRIPTION_PLANS if p.code == code), None)


def get_image_pack(code: str) -> ImagePack | None:
    return next((p for p in IMAGE_PACKS if p.code == code), None)


def get_feature(code: str) -> EmotionalFeature | None:
    return next((f for f in EMOTIONAL_FEATURES if f.code == code), None)
