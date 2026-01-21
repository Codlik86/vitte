"""
LLM Integration Module для Vitte Bot

Структура:
- personas/ - Все 8 персонажей с промптами и историями
- services/ - Сервисы (safety, intimacy, prompt_builder)
- constants/ - Константы (modes, atmospheres, safety_patterns)

Использование:
```python
from shared.llm import (
    # Персонажи
    get_persona,
    get_all_persona_keys,
    get_story,
    PERSONAS,

    # Prompt Builder
    ChatPromptContext,
    build_chat_messages,
    build_system_prompt,
    Message,

    # Safety
    run_safety_check,
    get_supportive_reply,

    # Intimacy
    decide_intimacy,
    is_sexting_message,

    # Constants
    get_mode_description,
    get_atmosphere_description,
)

# Пример использования:
persona = get_persona("lina")
print(persona["base_prompt"])

ctx = ChatPromptContext(
    persona_key="lina",
    mode="greeting_first",
)
messages = build_chat_messages(ctx)
```
"""

# Персонажи
from .personas import (
    PERSONAS,
    get_persona,
    get_all_persona_keys,
    get_persona_stories,
    get_story,
    # Отдельные персонажи
    LINA_METADATA, LINA_BASE_PROMPT, LINA_STORIES,
    MARIANNA_METADATA, MARIANNA_BASE_PROMPT, MARIANNA_STORIES,
    MEI_METADATA, MEI_BASE_PROMPT, MEI_STORIES,
    STACEY_METADATA, STACEY_BASE_PROMPT, STACEY_STORIES,
    YUNA_METADATA, YUNA_BASE_PROMPT, YUNA_STORIES,
    TAYA_METADATA, TAYA_BASE_PROMPT, TAYA_STORIES,
    JULIE_METADATA, JULIE_BASE_PROMPT, JULIE_STORIES,
    ASH_METADATA, ASH_BASE_PROMPT, ASH_STORIES,
)

# Сервисы
from .services import (
    # Safety
    SafetyResult,
    run_safety_check,
    get_supportive_reply,
    SAFETY_INSTRUCTION,
    # Intimacy
    IntimacyDecision,
    is_sexting_message,
    decide_intimacy,
    get_intimacy_instruction,
    SOFT_BLOCK_MESSAGES,
    PAYWALL_MESSAGES,
    # Prompt Builder
    Message,
    ChatPromptContext,
    PromptBuilder,
    build_chat_messages,
    build_system_prompt,
)

# Константы
from .constants import (
    # Режимы
    MODE_DESCRIPTIONS,
    get_mode_description,
    AVAILABLE_MODES,
    # Атмосферы
    ATMOSPHERE_DESCRIPTIONS,
    get_atmosphere_description,
    AVAILABLE_ATMOSPHERES,
    # Safety паттерны
    check_harm,
    check_illegal,
    check_minors,
    check_all,
)

__all__ = [
    # Персонажи
    "PERSONAS",
    "get_persona",
    "get_all_persona_keys",
    "get_persona_stories",
    "get_story",
    # Отдельные персонажи
    "LINA_METADATA", "LINA_BASE_PROMPT", "LINA_STORIES",
    "MARIANNA_METADATA", "MARIANNA_BASE_PROMPT", "MARIANNA_STORIES",
    "MEI_METADATA", "MEI_BASE_PROMPT", "MEI_STORIES",
    "STACEY_METADATA", "STACEY_BASE_PROMPT", "STACEY_STORIES",
    "YUNA_METADATA", "YUNA_BASE_PROMPT", "YUNA_STORIES",
    "TAYA_METADATA", "TAYA_BASE_PROMPT", "TAYA_STORIES",
    "JULIE_METADATA", "JULIE_BASE_PROMPT", "JULIE_STORIES",
    "ASH_METADATA", "ASH_BASE_PROMPT", "ASH_STORIES",
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
    # Режимы
    "MODE_DESCRIPTIONS",
    "get_mode_description",
    "AVAILABLE_MODES",
    # Атмосферы
    "ATMOSPHERE_DESCRIPTIONS",
    "get_atmosphere_description",
    "AVAILABLE_ATMOSPHERES",
    # Safety паттерны
    "check_harm",
    "check_illegal",
    "check_minors",
    "check_all",
]
