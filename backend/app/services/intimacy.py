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
    closeness_level = user_flags.get("closeness_level") if user_flags else None
    respect_score = user_flags.get("respect_score") if user_flags else None

    if respect_score is not None and respect_score < -3:
        return IntimacyResult(level=0, can_engage_intimately=False, label="обижена поведением")

    effective_closeness = closeness_level if closeness_level is not None else trust_level

    if message_count < 5 or effective_closeness < 10:
        return IntimacyResult(level=0, can_engage_intimately=False, label="знакомство")
    if message_count < 12 or trust_level < 35 or effective_closeness < 20:
        return IntimacyResult(level=1, can_engage_intimately=False, label="лёгкий флирт")

    if message_count < 18 or trust_level < 60 or effective_closeness < 40:
        return IntimacyResult(
            level=2,
            can_engage_intimately=deep_mode or premium or (trust_level >= 55 and effective_closeness >= 35),
            label="близость",
        )

    return IntimacyResult(
        level=3,
        can_engage_intimately=True,
        label="глубокие отношения",
    )
