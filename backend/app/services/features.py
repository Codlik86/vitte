from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

from ..models import User

FEATURE_DURATION_DAYS = 30


@dataclass
class FeatureState:
    code: str
    title: str
    description: str
    active: bool
    enabled: bool
    until: datetime | None
    product_code: str
    toggleable: bool = True


FEATURE_META: Dict[str, Dict[str, Any]] = {
    "long_letters": {
        "title": "Большие письма",
        "description": "Длинные, тёплые письма с глубиной и поддержкой.",
        "product_code": "long_letters_month",
        "toggleable": True,
    },
    "voice": {
        "title": "Голос персонажа",
        "description": "Получай голосовые ответы вместо обычного текста.",
        "product_code": "voice_month",
        "toggleable": True,
    },
    "deep_mode": {
        "title": "Глубокие отношения",
        "description": "Больше эмоциональности, флирта и искренности в ответах.",
        "product_code": "deep_mode_month",
        "toggleable": True,
    },
    "images": {
        "title": "Фантазии и образы",
        "description": "Персонаж может присылать визуальные сцены (заглушка).",
        "product_code": "fantasy_pack_month",
        "toggleable": False,
    },
}

FEATURE_ATTRS = {
    "long_letters": ("feature_long_letters_until", "feature_long_letters_enabled"),
    "voice": ("feature_voice_until", "feature_voice_enabled"),
    "deep_mode": ("feature_deep_mode_until", "feature_deep_mode_enabled"),
    "images": ("feature_images_until", None),
}


def _get_until(user: User, code: str) -> datetime | None:
    attr = FEATURE_ATTRS.get(code, (None, None))[0]
    return getattr(user, attr, None) if attr else None


def _get_enabled(user: User, code: str) -> bool:
    attr = FEATURE_ATTRS.get(code, (None, None))[1]
    value = getattr(user, attr, None) if attr else None
    return True if value is None else bool(value)


def _set_until(user: User, code: str, until: datetime | None):
    attr = FEATURE_ATTRS.get(code, (None, None))[0]
    if attr:
        setattr(user, attr, until)


def _set_enabled(user: User, code: str, enabled: bool):
    attr = FEATURE_ATTRS.get(code, (None, None))[1]
    if attr:
        setattr(user, attr, enabled)


def is_feature_active(user: User, code: str) -> bool:
    until = _get_until(user, code)
    enabled = _get_enabled(user, code)
    return bool(until and until > datetime.utcnow() and enabled)


def collect_feature_states(user: User) -> Dict[str, FeatureState]:
    states: Dict[str, FeatureState] = {}
    now = datetime.utcnow()
    for code, meta in FEATURE_META.items():
        until = _get_until(user, code)
        enabled = _get_enabled(user, code)
        active = bool(until and until > now and (enabled or not meta.get("toggleable", True)))
        states[code] = FeatureState(
            code=code,
            title=meta["title"],
            description=meta["description"],
            active=active,
            enabled=enabled,
            until=until,
            product_code=meta["product_code"],
            toggleable=meta.get("toggleable", True),
        )
    return states


def activate_feature(user: User, code: str, *, days: int = FEATURE_DURATION_DAYS, enable: bool = True) -> FeatureState:
    now = datetime.utcnow()
    current_until = _get_until(user, code)
    baseline = current_until if current_until and current_until > now else now
    new_until = baseline + timedelta(days=days)
    _set_until(user, code, new_until)
    if enable:
        _set_enabled(user, code, True)
    return collect_feature_states(user)[code]


def toggle_feature(user: User, code: str, enabled: bool) -> FeatureState:
    meta = FEATURE_META.get(code)
    if meta is None:
        raise ValueError("Unknown feature")
    if not meta.get("toggleable", True):
        return collect_feature_states(user)[code]
    _set_enabled(user, code, enabled)
    return collect_feature_states(user)[code]


def apply_product_purchase(user: User, product_code: str) -> list[FeatureState]:
    activated: List[FeatureState] = []
    for code, meta in FEATURE_META.items():
        if meta["product_code"] == product_code:
            activated.append(activate_feature(user, code))
    if not activated:
        raise ValueError("Product not linked to feature")
    return activated


def build_feature_instruction(states: Dict[str, FeatureState]) -> tuple[str, str | None, int | None]:
    """
    Returns (prompt, mode, max_tokens).
    """
    parts: List[str] = []
    mode: str | None = None
    max_tokens: int | None = None

    if states.get("deep_mode") and states["deep_mode"].active:
        parts.append(
            "Добавь эмоциональной глубины, искренности и мягкого флирта. "
            "Становись ближе, но оставайся безопасной и бережной."
        )
    if states.get("long_letters") and states["long_letters"].active:
        parts.append(
            "Пиши так, будто отправляешь тёплое длинное письмо: разворачивай мысли, "
            "делись чувствами и деталями, отвечай в 3–5 раз длиннее обычного."
        )
        mode = "long_letter_enhanced"
        max_tokens = 900
    if states.get("voice") and states["voice"].active:
        parts.append(
            "Формируй ответ так, будто записываешь голосовое: естественные интонации, без списков и сухих фактов."
        )

    prompt = " ".join(parts).strip()
    return prompt, mode, max_tokens


def any_feature_active(states: Iterable[FeatureState]) -> bool:
    return any(item.active for item in states)
