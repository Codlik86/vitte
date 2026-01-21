"""
Prompt Builder - модульный конструктор промптов для LLM

Собирает финальный system prompt из модульных блоков:
1. Блок персонажа (характер, стиль, триггеры)
2. Блок истории/сцены (если выбрана история)
3. Блок безопасности
4. Блок интимности
5. Блок режима диалога
6. Блок недавнего диалога
7. Блок памяти
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..personas import get_persona
from ..constants.modes import get_mode_description
from ..constants.atmospheres import get_atmosphere_description
from .safety import SAFETY_INSTRUCTION
from .intimacy import get_intimacy_instruction


@dataclass
class Message:
    """Сообщение в диалоге."""
    role: str  # "user" или "assistant"
    content: str


@dataclass
class ChatPromptContext:
    """Контекст для построения промпта."""
    persona_key: str  # Ключ персонажа (lina, marianna, etc.)
    user_name: Optional[str] = None  # Имя пользователя (если известно)

    # Режим и атмосфера
    mode: str = "default"  # greeting_first, greeting_return, auto_continue, etc.
    atmosphere: Optional[str] = None  # flirt_romance, support, cozy_evening, etc.

    # История/сцена
    story_key: Optional[str] = None  # Ключ истории персонажа

    # Память
    recent_messages: List[Message] = field(default_factory=list)
    memory_short: Optional[str] = None  # Краткая память (summary)
    memory_long: Optional[str] = None  # Долгая память (из Qdrant)

    # Интимность
    allow_intimate: bool = True
    soft_block_intimacy: bool = False

    # Фичи
    feature_instruction: Optional[str] = None
    voice_enabled: bool = False


class PromptBuilder:
    """Конструктор промптов."""

    def __init__(self, ctx: ChatPromptContext):
        self.ctx = ctx
        self.persona_data = get_persona(ctx.persona_key)
        self.metadata = self.persona_data["metadata"]
        self.base_prompt = self.persona_data["base_prompt"]
        self.stories = self.persona_data["stories"]

    def _build_persona_block(self) -> str:
        """Блок персонажа - базовый промпт."""
        return self.base_prompt

    def _build_story_block(self) -> str:
        """Блок истории/сцены (если выбрана история)."""
        if not self.ctx.story_key or self.ctx.story_key not in self.stories:
            return ""

        story = self.stories[self.ctx.story_key]
        return f"""
**История/сцена: {story['title']}**

{story['prompt']}
        """.strip()

    def _build_safety_block(self) -> str:
        """Блок безопасности."""
        return SAFETY_INSTRUCTION

    def _build_intimacy_block(self) -> str:
        """Блок интимности."""
        return get_intimacy_instruction(
            self.ctx.allow_intimate,
            self.ctx.soft_block_intimacy
        )

    def _build_mode_block(self) -> str:
        """Блок режима диалога."""
        mode_desc = get_mode_description(self.ctx.mode)

        result = f"""
**Режим диалога:**
{mode_desc}
        """.strip()

        # Добавляем атмосферу если указана
        if self.ctx.atmosphere:
            atm_desc = get_atmosphere_description(self.ctx.atmosphere)
            if atm_desc:
                result += f"""

**Атмосфера:**
{atm_desc}
                """.strip()

        return result

    def _build_recent_dialogue_block(self) -> str:
        """Блок недавнего диалога."""
        if not self.ctx.recent_messages:
            return ""

        # Берём последние 12 сообщений
        recent = self.ctx.recent_messages[-12:]

        lines = []
        for msg in recent:
            role = "Пользователь" if msg.role == "user" else self.metadata["name"]
            # Ограничиваем длину сообщения
            content = msg.content[:500]
            if len(msg.content) > 500:
                content += "..."
            lines.append(f"{role}: {content}")

        dialogue_text = "\n".join(lines)

        return f"""
**Последние сообщения диалога:**
(Используй их чтобы продолжить разговор естественно)

{dialogue_text}
        """.strip()

    def _build_memory_block(self) -> str:
        """Блок памяти (краткая + долгая)."""
        parts = []

        if self.ctx.memory_short:
            parts.append(f"""
**Краткая память:**
{self.ctx.memory_short}
            """.strip())

        if self.ctx.memory_long:
            parts.append(f"""
**Долгая память (факты о пользователе):**
{self.ctx.memory_long}
            """.strip())

        if not parts:
            parts.append("""
**Память:**
Нет особых воспоминаний, но ты открыта к новым разговорам и готова узнать собеседника лучше.
            """.strip())

        return "\n\n".join(parts)

    def _build_features_block(self) -> str:
        """Блок платных фич."""
        if not self.ctx.feature_instruction:
            return ""

        result = f"""
**Режим улучшений:**
{self.ctx.feature_instruction}
        """.strip()

        if self.ctx.voice_enabled:
            result += """

**Голосовой режим:**
Твои ответы будут озвучены. Пиши более разговорно,
избегай сложных конструкций и длинных предложений.
            """.strip()

        return result

    def build_system_prompt(self) -> str:
        """
        Собрать полный system prompt из всех блоков.

        Returns:
            Полный текст system prompt
        """
        blocks = [
            self._build_persona_block(),
            self._build_story_block(),
            self._build_safety_block(),
            self._build_intimacy_block(),
            self._build_mode_block(),
            self._build_memory_block(),
            self._build_features_block(),
        ]

        # Фильтруем пустые блоки
        blocks = [b for b in blocks if b.strip()]

        return "\n\n---\n\n".join(blocks)

    def build_messages(self, user_message: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Собрать список сообщений для отправки в LLM.

        Args:
            user_message: Текущее сообщение пользователя (если есть)

        Returns:
            Список сообщений в формате OpenAI
        """
        messages = [
            {"role": "system", "content": self.build_system_prompt()}
        ]

        # Добавляем историю диалога
        for msg in self.ctx.recent_messages[-10:]:  # Последние 10 сообщений
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Добавляем текущее сообщение пользователя
        if user_message:
            messages.append({
                "role": "user",
                "content": user_message
            })

        return messages


def build_chat_messages(ctx: ChatPromptContext, user_message: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Удобная функция для построения сообщений.

    Args:
        ctx: Контекст промпта
        user_message: Текущее сообщение пользователя

    Returns:
        Список сообщений для LLM
    """
    builder = PromptBuilder(ctx)
    return builder.build_messages(user_message)


def build_system_prompt(ctx: ChatPromptContext) -> str:
    """
    Удобная функция для построения system prompt.

    Args:
        ctx: Контекст промпта

    Returns:
        Текст system prompt
    """
    builder = PromptBuilder(ctx)
    return builder.build_system_prompt()


__all__ = [
    "Message",
    "ChatPromptContext",
    "PromptBuilder",
    "build_chat_messages",
    "build_system_prompt",
]
