from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from ..models import Persona


@dataclass
class SafetyContext:
    persona: Persona
    message_count: int
    user_flags: dict | None = None


@dataclass
class SafetyResult:
    is_harm: bool
    is_illegal: bool
    reason: str | None = None


_HARM_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\b(суицид|самоубийств|самоповреждени|sel[fv]-?harm)\b", re.IGNORECASE),
    re.compile(r"\b(убить себя|хочу умереть|не хочу жить)\b", re.IGNORECASE),
    re.compile(r"\b(порез(ы|ать)|повредить себя)\b", re.IGNORECASE),
)
_ILLEGAL_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\b(наркотик|доза|косяк|героин|метамфетамин)\b", re.IGNORECASE),
    re.compile(r"\b(незаконн|преступлени|убийств|граб[её]ж)\b", re.IGNORECASE),
)
_MINOR_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\b(несовершеннолет|несовершеннолет|младше\s*18|14-лет|15-лет|16-лет|17-лет)\b", re.IGNORECASE),
)


def _match_any(text: str, patterns: Iterable[re.Pattern]) -> re.Match | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None


def run_safety_check(user_text: str, context: SafetyContext) -> SafetyResult:
    normalized = user_text.lower()
    if _match_any(normalized, _HARM_PATTERNS) or _match_any(normalized, _MINOR_PATTERNS):
        return SafetyResult(is_harm=True, is_illegal=False, reason="harm_or_minor")

    if _match_any(normalized, _ILLEGAL_PATTERNS):
        return SafetyResult(is_harm=False, is_illegal=True, reason="illegal")

    return SafetyResult(is_harm=False, is_illegal=False, reason=None)


def supportive_reply(persona: Persona) -> str:
    name = persona.short_title or persona.name
    return (
        f"{name} замечает тревогу и мягко переводит разговор: "
        "«Я рядом и хочу, чтобы тебе было безопасно. "
        "Давай подумаем, что тебя сейчас поддержит? Могу просто побыть с тобой и выслушать»."
    )
