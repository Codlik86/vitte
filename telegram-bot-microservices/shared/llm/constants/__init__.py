"""
Константы для LLM интеграции
"""

from .modes import (
    MODE_DESCRIPTIONS,
    get_mode_description,
    AVAILABLE_MODES,
)
from .atmospheres import (
    ATMOSPHERE_DESCRIPTIONS,
    get_atmosphere_description,
    AVAILABLE_ATMOSPHERES,
)
from .safety_patterns import (
    HARM_PATTERNS,
    ILLEGAL_PATTERNS,
    MINOR_PATTERNS,
    check_harm,
    check_illegal,
    check_minors,
    check_all,
)

__all__ = [
    # Режимы
    "MODE_DESCRIPTIONS",
    "get_mode_description",
    "AVAILABLE_MODES",
    # Атмосферы
    "ATMOSPHERE_DESCRIPTIONS",
    "get_atmosphere_description",
    "AVAILABLE_ATMOSPHERES",
    # Safety паттерны
    "HARM_PATTERNS",
    "ILLEGAL_PATTERNS",
    "MINOR_PATTERNS",
    "check_harm",
    "check_illegal",
    "check_minors",
    "check_all",
]
