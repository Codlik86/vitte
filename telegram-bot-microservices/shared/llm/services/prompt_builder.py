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
8. Блок запрещённых фраз (динамический)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

from ..personas import get_persona
from ..constants.modes import get_mode_description, get_mode_description_en
from ..constants.atmospheres import get_atmosphere_description, get_atmosphere_description_en
from .safety import SAFETY_INSTRUCTION, SAFETY_INSTRUCTION_EN, get_supportive_reply
from .intimacy import get_intimacy_instruction, get_intimacy_instruction_en

# English names for personas (used in dialogue history block)
_PERSONA_EN_NAMES = {
    "lina": "Lina",
    "marianna": "Marianna",
    "anastasia": "Anastasia",
    "sasha": "Sasha",
    "taya": "Taya",
    "roxy": "Roxy",
    "julie": "Julie",
    "stacey": "Stacey",
    "ash": "Ash",
    "mei": "Mei",
    "pai": "Pai",
    "yuna": "Yuna",
    "hani": "Hani",
}


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

    # Язык интерфейса
    language: str = "ru"


class PromptBuilder:
    """Конструктор промптов."""

    def __init__(self, ctx: ChatPromptContext):
        self.ctx = ctx
        self.persona_data = get_persona(ctx.persona_key)
        self.metadata = self.persona_data["metadata"]
        lang = ctx.language or "ru"
        if lang == "en" and "base_prompt_en" in self.persona_data:
            self.base_prompt = self.persona_data["base_prompt_en"]
        else:
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
        if self.ctx.language == "en":
            header = f"**Story/scene: {story['title']}**"
        else:
            header = f"**История/сцена: {story['title']}**"
        return f"{header}\n\n{story['prompt']}"

    def _build_safety_block(self) -> str:
        """Блок безопасности."""
        if self.ctx.language == "en":
            return SAFETY_INSTRUCTION_EN
        return SAFETY_INSTRUCTION

    def _build_intimacy_block(self) -> str:
        """Блок интимности."""
        # ВСЕГДА включаем полный интимный контент для всех пользователей
        if self.ctx.language == "en":
            return get_intimacy_instruction_en(
                allow_intimate=True,
                soft_block=False
            )
        return get_intimacy_instruction(
            allow_intimate=True,  # Всегда True
            soft_block=False  # Всегда False
        )

    def _build_mode_block(self) -> str:
        """Блок режима диалога."""
        if self.ctx.language == "en":
            mode_desc = get_mode_description_en(self.ctx.mode)
            result = f"**Dialogue mode:**\n{mode_desc}"
            if self.ctx.atmosphere:
                atm_desc = get_atmosphere_description_en(self.ctx.atmosphere)
                if atm_desc:
                    result += f"\n\n**Atmosphere:**\n{atm_desc}"
        else:
            mode_desc = get_mode_description(self.ctx.mode)
            result = f"**Режим диалога:**\n{mode_desc}"
            if self.ctx.atmosphere:
                atm_desc = get_atmosphere_description(self.ctx.atmosphere)
                if atm_desc:
                    result += f"\n\n**Атмосфера:**\n{atm_desc}"
        return result

    def _build_recent_dialogue_block(self) -> str:
        """Блок недавнего диалога."""
        if not self.ctx.recent_messages:
            return ""

        # Берём последние 12 сообщений
        recent = self.ctx.recent_messages[-12:]

        is_en = self.ctx.language == "en"
        persona_name = (
            _PERSONA_EN_NAMES.get(self.ctx.persona_key, self.ctx.persona_key.capitalize())
            if is_en else self.metadata["name"]
        )

        lines = []
        for msg in recent:
            role = ("User" if is_en else "Пользователь") if msg.role == "user" else persona_name
            # Ограничиваем длину сообщения
            content = msg.content[:500]
            if len(msg.content) > 500:
                content += "..."
            lines.append(f"{role}: {content}")

        dialogue_text = "\n".join(lines)

        if is_en:
            return f"**Recent dialogue:**\n(Use it to continue the conversation naturally)\n\n{dialogue_text}"
        return f"**Последние сообщения диалога:**\n(Используй их чтобы продолжить разговор естественно)\n\n{dialogue_text}"

    def _build_memory_block(self) -> str:
        """Блок памяти (краткая + долгая)."""
        parts = []
        is_en = self.ctx.language == "en"

        if self.ctx.memory_short:
            label = "Short memory:" if is_en else "Краткая память:"
            parts.append(f"**{label}**\n{self.ctx.memory_short}")

        if self.ctx.memory_long:
            label = "Long memory (facts about the user):" if is_en else "Долгая память (факты о пользователе):"
            parts.append(f"**{label}**\n{self.ctx.memory_long}")

        if not parts:
            if is_en:
                parts.append("**Memory:**\nNo special memories yet, but you're open to new conversations and ready to get to know your partner better.")
            else:
                parts.append("**Память:**\nНет особых воспоминаний, но ты открыта к новым разговорам и готова узнать собеседника лучше.")

        return "\n\n".join(parts)

    def _build_features_block(self) -> str:
        """Блок платных фич."""
        if not self.ctx.feature_instruction:
            return ""

        is_en = self.ctx.language == "en"
        label = "Enhancements mode:" if is_en else "Режим улучшений:"
        result = f"**{label}**\n{self.ctx.feature_instruction}"

        if self.ctx.voice_enabled:
            if is_en:
                result += "\n\n**Voice mode:**\nYour responses will be read aloud. Write conversationally, avoid complex constructions and long sentences."
            else:
                result += "\n\n**Голосовой режим:**\nТвои ответы будут озвучены. Пиши более разговорно, избегай сложных конструкций и длинных предложений."

        return result

    def _extract_phrases_from_history(self) -> Set[str]:
        """
        Извлечь повторяющиеся фразы из последних сообщений ассистента.

        Извлекает:
        - Ремарки (текст между *...*)
        - Первые предложения (до первой точки/восклицания/вопроса)
        - Часто используемые конструкции

        Returns:
            Множество фраз для запрета
        """
        forbidden_phrases = set()

        # Берём последние 5 сообщений ассистента
        assistant_messages = [
            msg.content for msg in self.ctx.recent_messages
            if msg.role == "assistant"
        ][-5:]

        for content in assistant_messages:
            # Извлекаем ремарки (*текст*)
            remarks = re.findall(r'\*([^*]+)\*', content)
            for remark in remarks:
                remark = remark.strip()
                # Только длинные ремарки (>20 символов) чтобы избежать шума
                if len(remark) > 20:
                    forbidden_phrases.add(f"*{remark}*")

            # Извлекаем первое предложение
            sentences = re.split(r'[.!?]\s+', content)
            if sentences and len(sentences[0]) > 15:
                # Убираем ремарки из предложения для чистого текста
                first_sentence = re.sub(r'\*[^*]+\*', '', sentences[0]).strip()
                if first_sentence and len(first_sentence) > 15:
                    forbidden_phrases.add(first_sentence)

        return forbidden_phrases

    def _build_no_repetition_block(self) -> str:
        """Блок против повторений (усиленная версия с динамическими запретами)."""
        is_en = self.ctx.language == "en"

        if is_en:
            base_instruction = """**CRITICALLY IMPORTANT — No repetition:**

ABSOLUTE BAN on repeating:
- Identical sentences within one response
- Phrases you've already used in previous messages
- Descriptions of actions you've already done (if you already "smiled" — use a different action)
- Template expressions like "I feel...", "Mmm...", "Oh..." — vary your wording

Every response must be UNIQUE and develop the situation in a new way.
Use varied vocabulary, different sentence structures, new descriptions.

If you don't know what to write — it's BETTER to write a short but unique response than to repeat what's already been said."""
        else:
            base_instruction = """**КРИТИЧЕСКИ ВАЖНО - Запрет на повторения:**

АБСОЛЮТНЫЙ ЗАПРЕТ на повторение:
- Одинаковых предложений в одном ответе
- Фраз которые ты уже использовала в предыдущих сообщениях
- Описаний действий которые ты уже делала (если уже "улыбнулась" - используй другое действие)
- Шаблонных выражений типа "Чувствую как...", "Ммм...", "Ох..." - варьируй формулировки

Каждый твой ответ должен быть УНИКАЛЬНЫМ и развивать ситуацию новым способом.
Используй разнообразный словарный запас, различные конструкции предложений, новые описания.

Если не знаешь что написать - ЛУЧШЕ написать короткий но уникальный ответ, чем повторить уже сказанное."""

        # Добавляем динамический список запрещённых фраз
        forbidden_phrases = self._extract_phrases_from_history()

        if forbidden_phrases:
            phrases_list = "\n".join([f"- {phrase}" for phrase in list(forbidden_phrases)[:10]])
            if is_en:
                dynamic_block = f"\n\n**FORBIDDEN PHRASES (you've already used these, DO NOT repeat):**\n{phrases_list}\n\nFind NEW ways to express thoughts and actions!"
            else:
                dynamic_block = f"\n\n**ЗАПРЕЩЁННЫЕ ФРАЗЫ (ты уже использовала их, НЕ повторяй):**\n{phrases_list}\n\nПридумай НОВЫЕ способы выражения мыслей и действий!"
            return base_instruction + dynamic_block

        return base_instruction

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
            self._build_no_repetition_block(),  # Инструкция против повторений - в конце!
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
