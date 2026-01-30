"""
Сервисы для LLM интеграции
"""

from .safety import (
    SafetyResult,
    run_safety_check,
    get_supportive_reply,
    SAFETY_INSTRUCTION,
)
from .intimacy import (
    IntimacyDecision,
    is_sexting_message,
    decide_intimacy,
    get_intimacy_instruction,
    SOFT_BLOCK_MESSAGES,
    PAYWALL_MESSAGES,
)
from .prompt_builder import (
    Message,
    ChatPromptContext,
    PromptBuilder,
    build_chat_messages,
    build_system_prompt,
)

__all__ = [
    # Safety
    "SafetyResult",
    "run_safety_check",
    "get_supportive_reply",
    "SAFETY_INSTRUCTION",
    # Intimacy
    "IntimacyDecision",
    "is_sexting_message",
    "decide_intimacy",
    "get_intimacy_instruction",
    "SOFT_BLOCK_MESSAGES",
    "PAYWALL_MESSAGES",
    # Prompt Builder
    "Message",
    "ChatPromptContext",
    "PromptBuilder",
    "build_chat_messages",
    "build_system_prompt",
]
