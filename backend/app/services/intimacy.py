from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntimacyResult:
    level: int  # 0-3
    can_engage_intimately: bool
    label: str


def evaluate_intimacy(
    *,
    trust_level: int,
    message_count: int,
    user_flags: dict | None = None,
) -> IntimacyResult:
    """
    Простая лестница: до 10-15 сообщений — мягкий флирт и узнавание,
    дальше — можно идти в близость при достаточном доверии.
    """
    premium = bool(user_flags.get("has_subscription")) if user_flags else False
    deep_mode = bool(user_flags.get("deep_mode")) if user_flags else False

    if message_count < 5:
        return IntimacyResult(level=0, can_engage_intimately=False, label="знакомство")
    if message_count < 12 or trust_level < 35:
        return IntimacyResult(level=1, can_engage_intimately=False, label="лёгкий флирт")

    if message_count < 18 or trust_level < 60:
        return IntimacyResult(
            level=2,
            can_engage_intimately=deep_mode or premium or trust_level >= 55,
            label="близость",
        )

    return IntimacyResult(
        level=3,
        can_engage_intimately=True,
        label="глубокие отношения",
    )
