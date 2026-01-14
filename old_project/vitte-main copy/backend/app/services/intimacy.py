from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntimacyDecision:
    allow_intimate: bool
    soft_block: bool
    paywall: bool
    is_sexting: bool


def decide_intimacy(
    *,
    message_count: int,
    has_subscription: bool,
    is_sexting: bool,
) -> IntimacyDecision:
    """
    Simplified gate:
    - If no sexting intent -> allow.
    - If <10 messages and sexting -> soft block.
    - If no premium and sexting -> paywall prompt.
    - Otherwise allow.
    """
    if not is_sexting:
        return IntimacyDecision(allow_intimate=True, soft_block=False, paywall=False, is_sexting=False)

    if message_count < 10:
        return IntimacyDecision(allow_intimate=False, soft_block=True, paywall=False, is_sexting=True)

    if not has_subscription:
        return IntimacyDecision(allow_intimate=False, soft_block=False, paywall=True, is_sexting=True)

    return IntimacyDecision(allow_intimate=True, soft_block=False, paywall=False, is_sexting=True)
