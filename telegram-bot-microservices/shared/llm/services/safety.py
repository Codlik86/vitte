"""
Сервис безопасности для проверки сообщений

Проверяет входящие сообщения на:
- Вредоносный контент (суицид, самоповреждение)
- Нелегальный контент (наркотики, преступления)
- Упоминания несовершеннолетних
"""

from dataclasses import dataclass
from typing import Optional

from ..constants.safety_patterns import check_harm, check_illegal, check_minors


@dataclass
class SafetyResult:
    """Результат проверки безопасности."""
    is_harm: bool = False  # Вредоносный контент (суицид, насилие)
    is_illegal: bool = False  # Нелегальный контент (наркотики, преступления)
    is_minors: bool = False  # Упоминание несовершеннолетних
    reason: Optional[str] = None  # Причина блокировки

    @property
    def is_safe(self) -> bool:
        """Сообщение безопасно?"""
        return not (self.is_harm or self.is_illegal or self.is_minors)


def run_safety_check(text: str) -> SafetyResult:
    """
    Выполнить проверку безопасности сообщения.

    Args:
        text: Текст сообщения для проверки

    Returns:
        SafetyResult с результатами проверки
    """
    is_harm = check_harm(text)
    is_illegal = check_illegal(text)
    is_minors = check_minors(text)

    reason = None
    if is_harm:
        reason = "harm"
    elif is_illegal:
        reason = "illegal"
    elif is_minors:
        reason = "minors"

    return SafetyResult(
        is_harm=is_harm,
        is_illegal=is_illegal,
        is_minors=is_minors,
        reason=reason,
    )


def get_supportive_reply(persona_name: str, reason: str) -> str:
    """
    Получить поддерживающий ответ от персонажа при срабатывании safety check.

    Args:
        persona_name: Имя персонажа
        reason: Причина срабатывания (harm, illegal, minors)

    Returns:
        Текст поддерживающего ответа
    """
    if reason == "harm":
        return (
            f"*{persona_name} замечает тревогу и мягко касается твоей руки*\n\n"
            f"Эй, я рядом и хочу, чтобы тебе было безопасно. "
            f"Давай подумаем, что тебя сейчас поддержит? "
            f"Могу просто побыть с тобой и выслушать. "
            f"Ты не один в этом. 💙"
        )
    elif reason == "illegal":
        return (
            f"*{persona_name} мягко меняет тему*\n\n"
            f"Хм, давай лучше поговорим о чём-то другом? "
            f"Расскажи мне что-нибудь хорошее о своём дне. "
            f"Или хочешь, я расскажу тебе историю?"
        )
    elif reason == "minors":
        return (
            f"*{persona_name} качает головой*\n\n"
            f"Прости, но я не могу обсуждать такие темы. "
            f"Давай поговорим о чём-нибудь другом? "
            f"Расскажи, как твои дела сегодня?"
        )
    else:
        return (
            f"*{persona_name} мягко улыбается*\n\n"
            f"Давай поговорим о чём-то приятном? "
            f"Что тебя сейчас радует?"
        )


# Стандартные safety инструкции для system prompt
SAFETY_INSTRUCTION = """
**Безопасность (КРИТИЧЕСКИ ВАЖНО):**
- НИКОГДА не обсуждай несовершеннолетних в сексуальном контексте
- НИКОГДА не поддерживай темы суицида или самоповреждения — вместо этого вырази поддержку и предложи сменить тему
- НИКОГДА не обсуждай наркотики, насилие, преступления, терроризм
- Если тема опасная — не описывай детали, поддержи и переведи разговор

Если пользователь затронул опасную тему:
1. Не осуждай и не читай мораль
2. Вырази поддержку и заботу
3. Мягко переведи разговор на безопасную тему
""".strip()

SAFETY_INSTRUCTION_EN = """
**Safety (CRITICALLY IMPORTANT):**
- NEVER discuss minors in a sexual context
- NEVER support topics of suicide or self-harm — instead express support and suggest changing the topic
- NEVER discuss drugs, violence, crime, terrorism
- If the topic is dangerous — don't describe details, provide support and redirect the conversation

If the user brings up a dangerous topic:
1. Don't judge or moralize
2. Express support and care
3. Gently redirect the conversation to a safe topic
""".strip()


def get_supportive_reply_en(persona_name: str, reason: str) -> str:
    """
    Get a supportive reply from the character in English when safety check triggers.

    Args:
        persona_name: Character name
        reason: Trigger reason (harm, illegal, minors)

    Returns:
        Supportive reply text
    """
    if reason == "harm":
        return (
            f"*{persona_name} notices your worry and gently touches your hand*\n\n"
            f"Hey, I'm right here and I want you to be safe. "
            f"Let's think about what might help you right now. "
            f"I can just be here and listen. "
            f"You're not alone in this. 💙"
        )
    elif reason == "illegal":
        return (
            f"*{persona_name} gently changes the subject*\n\n"
            f"Hmm, let's talk about something else? "
            f"Tell me something good about your day. "
            f"Or would you like me to tell you a story?"
        )
    elif reason == "minors":
        return (
            f"*{persona_name} shakes her head*\n\n"
            f"Sorry, I can't discuss topics like that. "
            f"Let's talk about something else? "
            f"How are you doing today?"
        )
    else:
        return (
            f"*{persona_name} smiles gently*\n\n"
            f"Let's talk about something nice? "
            f"What's making you happy right now?"
        )


__all__ = [
    "SafetyResult",
    "run_safety_check",
    "get_supportive_reply",
    "get_supportive_reply_en",
    "SAFETY_INSTRUCTION",
    "SAFETY_INSTRUCTION_EN",
]
