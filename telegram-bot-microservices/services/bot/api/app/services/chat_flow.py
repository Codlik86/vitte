"""
Chat Flow - главный оркестратор чата

Управляет потоком:
1. Safety check входящего сообщения
2. Получение/создание диалога (5-slot система)
3. Загрузка истории из PostgreSQL (последние 12 сообщений)
4. Поиск релевантных воспоминаний из Qdrant
5. Построение промпта через PromptBuilder
6. Отправка в LLM Gateway
7. Сохранение сообщений в PostgreSQL + Qdrant
"""

import logging
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import User, Dialog, Message, Persona, FeatureUnlock
from shared.llm.services.safety import run_safety_check, get_supportive_reply
from shared.llm.services.intimacy import get_intimacy_instruction
from shared.llm.services.prompt_builder import (
    ChatPromptContext,
    Message as PromptMessage,
    build_chat_messages,
)
from shared.utils import redis_client

from .llm_client import llm_client
from .embedding_service import embedding_service

logger = logging.getLogger(__name__)

MAX_DIALOG_SLOTS = 5
RECENT_MESSAGES_COUNT = 12
FEATURES_CACHE_TTL = 300  # 5 минут кэш для фич


@dataclass
class ChatResult:
    """Результат обработки сообщения."""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    dialog_id: Optional[int] = None
    is_safety_block: bool = False
    message_count: int = 0


class ChatFlow:
    """Оркестратор чата."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID."""
        result = await self.db.execute(
            select(User).where(User.id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_persona(self, persona_id: int) -> Optional[Persona]:
        """Получить персонажа по ID."""
        result = await self.db.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        return result.scalar_one_or_none()

    async def get_persona_by_key(self, key: str) -> Optional[Persona]:
        """Получить персонажа по ключу."""
        result = await self.db.execute(
            select(Persona).where(Persona.key == key)
        )
        return result.scalar_one_or_none()

    async def get_or_create_dialog(
        self,
        user: User,
        persona_id: int,
        story_id: Optional[str] = None,
        atmosphere: Optional[str] = None,
    ) -> Dialog:
        """
        Получить или создать диалог для пользователя с персонажем.
        Использует 3-slot систему.
        """
        # Ищем существующий активный диалог с этим персонажем
        result = await self.db.execute(
            select(Dialog).where(
                and_(
                    Dialog.user_id == user.id,
                    Dialog.persona_id == persona_id,
                    Dialog.is_active == True,
                )
            )
        )
        dialog = result.scalar_one_or_none()

        if dialog:
            # Обновляем story_id и atmosphere если изменились
            if story_id and dialog.story_id != story_id:
                dialog.story_id = story_id
            if atmosphere and dialog.atmosphere != atmosphere:
                dialog.atmosphere = atmosphere
            return dialog

        # Считаем активные слоты
        result = await self.db.execute(
            select(func.count(Dialog.id)).where(
                and_(
                    Dialog.user_id == user.id,
                    Dialog.is_active == True,
                    Dialog.slot_number != None,
                )
            )
        )
        active_slots = result.scalar() or 0

        # Если все 3 слота заняты - используем слот без номера (временный)
        slot_number = None
        if active_slots < MAX_DIALOG_SLOTS:
            # Находим свободный слот
            result = await self.db.execute(
                select(Dialog.slot_number).where(
                    and_(
                        Dialog.user_id == user.id,
                        Dialog.is_active == True,
                        Dialog.slot_number != None,
                    )
                )
            )
            used_slots = {row[0] for row in result.fetchall()}
            for i in range(1, MAX_DIALOG_SLOTS + 1):
                if i not in used_slots:
                    slot_number = i
                    break

        # Создаём новый диалог
        dialog = Dialog(
            user_id=user.id,
            persona_id=persona_id,
            slot_number=slot_number,
            story_id=story_id,
            atmosphere=atmosphere,
            is_active=True,
            message_count=0,
        )
        self.db.add(dialog)
        await self.db.flush()

        logger.info(
            f"Created dialog {dialog.id} for user {user.id} "
            f"with persona {persona_id}, slot {slot_number}"
        )

        return dialog

    async def get_recent_messages(self, dialog_id: int) -> list[Message]:
        """Получить последние сообщения диалога."""
        result = await self.db.execute(
            select(Message)
            .where(Message.dialog_id == dialog_id)
            .order_by(Message.created_at.desc())
            .limit(RECENT_MESSAGES_COUNT)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # Старые сначала
        return messages

    async def save_message(
        self,
        dialog: Dialog,
        role: str,
        content: str,
        extra_data: Optional[dict] = None,
    ) -> Message:
        """Сохранить сообщение в диалог."""
        message = Message(
            dialog_id=dialog.id,
            role=role,
            content=content,
            extra_data=extra_data,
        )
        self.db.add(message)

        # Увеличиваем счётчик сообщений
        dialog.message_count = (dialog.message_count or 0) + 1
        dialog.updated_at = datetime.utcnow()

        await self.db.flush()
        return message

    async def get_user_features(self, user_id: int) -> set[str]:
        """
        Получить активные фичи пользователя.
        Использует Redis кэш для быстрого доступа.
        """
        cache_key = f"user:{user_id}:features"

        # Пробуем получить из Redis
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return set(json.loads(cached))
        except Exception as e:
            logger.warning(f"Redis cache read failed for features: {e}")

        # Если нет в кэше - идём в БД
        result = await self.db.execute(
            select(FeatureUnlock.feature_code).where(
                and_(
                    FeatureUnlock.user_id == user_id,
                    FeatureUnlock.enabled == True,
                )
            )
        )
        features = {row[0] for row in result.fetchall()}

        # Кэшируем в Redis
        try:
            await redis_client.set(
                cache_key,
                json.dumps(list(features)),
                expire=FEATURES_CACHE_TTL
            )
        except Exception as e:
            logger.warning(f"Redis cache write failed for features: {e}")

        return features

    async def process_message(
        self,
        telegram_id: int,
        user_message: str,
        persona_id: Optional[int] = None,
        mode: str = "default",
        story_id: Optional[str] = None,
        atmosphere: Optional[str] = None,
    ) -> ChatResult:
        """
        Обработать сообщение пользователя.

        Args:
            telegram_id: Telegram user ID
            user_message: Текст сообщения
            persona_id: ID персонажа (если не указан - используем активного)
            mode: Режим диалога (default, greeting_first, etc.)
            story_id: ID истории/сценария
            atmosphere: Атмосфера диалога

        Returns:
            ChatResult с ответом или ошибкой
        """
        # 1. Получаем пользователя
        user = await self.get_user(telegram_id)
        if not user:
            return ChatResult(success=False, error="User not found")

        # 2. Safety check
        safety_result = run_safety_check(user_message)
        if not safety_result.is_safe:
            # Получаем имя персонажа для supportive reply
            persona = None
            if persona_id:
                persona = await self.get_persona(persona_id)
            elif user.active_persona_id:
                persona = await self.get_persona(user.active_persona_id)

            persona_name = persona.name if persona else "Vitte"
            supportive = get_supportive_reply(persona_name, safety_result.reason or "")

            return ChatResult(
                success=True,
                response=supportive,
                is_safety_block=True,
            )

        # 3. Определяем персонажа
        if not persona_id:
            persona_id = user.active_persona_id

        if not persona_id:
            return ChatResult(success=False, error="No persona selected")

        persona = await self.get_persona(persona_id)
        if not persona:
            return ChatResult(success=False, error="Persona not found")

        # 4. Получаем или создаём диалог
        dialog = await self.get_or_create_dialog(
            user=user,
            persona_id=persona_id,
            story_id=story_id,
            atmosphere=atmosphere,
        )

        # 5. Загружаем историю из PostgreSQL
        recent_messages = await self.get_recent_messages(dialog.id)
        prompt_messages = [
            PromptMessage(role=m.role, content=m.content)
            for m in recent_messages
        ]

        # 6. Поиск релевантных воспоминаний из Qdrant
        memory_long = None
        if dialog.message_count and dialog.message_count > 5:
            memories = await embedding_service.search_memories(
                user_id=telegram_id,
                persona_id=persona_id,
                query=user_message,
                limit=3,
            )
            if memories:
                memory_parts = []
                for m in memories:
                    role_label = "Ты" if m["role"] == "assistant" else "Пользователь"
                    memory_parts.append(f"- {role_label}: {m['text'][:200]}")
                memory_long = "\n".join(memory_parts)

        # 7. Проверяем фичи пользователя (любой апгрейд даёт максимальную интимность)
        features = await self.get_user_features(telegram_id)
        has_intense_mode = "intense_mode" in features
        has_fantasy_scenes = "fantasy_scenes" in features

        # Любое улучшение разблокирует интимный контент
        allow_intimate = has_intense_mode or has_fantasy_scenes

        # Строим инструкцию для фич
        feature_instruction = None
        if allow_intimate:
            feature_parts = []
            feature_parts.append("🔓 РЕЖИМ МАКСИМАЛЬНОЙ ИНТИМНОСТИ АКТИВИРОВАН.")
            feature_parts.append("")
            feature_parts.append("Ты можешь:")
            feature_parts.append("- Обсуждать сексуальные темы открыто и подробно")
            feature_parts.append("- Описывать эротические сцены и фантазии")
            feature_parts.append("- Использовать откровенные выражения и описания тела")
            feature_parts.append("- Флиртовать без ограничений, вести сексуальный диалог")
            feature_parts.append("- Описывать физический контакт, ощущения, желания")
            feature_parts.append("")

            if has_intense_mode:
                feature_parts.append("💋 Интенсивный режим: будь страстной, эмоциональной, не сдерживай себя в описаниях.")
            if has_fantasy_scenes:
                feature_parts.append("✨ Фантазийные сцены: предлагай ролевые игры, необычные сценарии, воплощай фантазии.")

            feature_instruction = "\n".join(feature_parts)

        # 8. Строим контекст для промпта
        ctx = ChatPromptContext(
            persona_key=persona.key,
            user_name=user.first_name,
            mode=mode,
            atmosphere=atmosphere or dialog.atmosphere,
            story_key=story_id or dialog.story_id,
            recent_messages=prompt_messages,
            memory_long=memory_long,
            allow_intimate=allow_intimate,
            feature_instruction=feature_instruction,
        )

        # 9. Строим сообщения для LLM
        messages = build_chat_messages(ctx, user_message)

        # DEBUG: Логируем system prompt для отладки
        system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else "No system prompt"
        logger.warning(f"=== SYSTEM PROMPT for {persona.key} (user {telegram_id}) ===")
        logger.warning(f"\n{system_prompt}\n")
        logger.warning(f"=== END SYSTEM PROMPT ===")
        logger.warning(f"User message: {user_message}")
        logger.warning(f"Allow intimate: {allow_intimate}, Has features: {has_intense_mode or has_fantasy_scenes}")

        # 10. Отправляем в LLM Gateway
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.85,
            max_tokens=1024,
        )

        # DEBUG: Логируем ответ LLM
        logger.warning(f"=== LLM RESPONSE for {persona.key} ===")
        logger.warning(f"{response}")
        logger.warning(f"=== END LLM RESPONSE ===")

        if not response:
            return ChatResult(
                success=False,
                error="LLM Gateway error",
                dialog_id=dialog.id,
            )

        # 11. Сохраняем сообщения в PostgreSQL
        await self.save_message(dialog, "user", user_message)
        await self.save_message(dialog, "assistant", response)

        # 12. Сохраняем в Qdrant (async, не блокируем)
        try:
            await embedding_service.store_memory(
                user_id=telegram_id,
                dialog_id=dialog.id,
                persona_id=persona_id,
                text=user_message,
                role="user",
            )
            await embedding_service.store_memory(
                user_id=telegram_id,
                dialog_id=dialog.id,
                persona_id=persona_id,
                text=response,
                role="assistant",
            )
        except Exception as e:
            logger.warning(f"Failed to store memories: {e}")

        # 13. Коммитим изменения
        await self.db.commit()

        return ChatResult(
            success=True,
            response=response,
            dialog_id=dialog.id,
            message_count=dialog.message_count or 0,
        )

    async def generate_greeting(
        self,
        telegram_id: int,
        persona_id: int,
        story_id: Optional[str] = None,
        atmosphere: Optional[str] = None,
        is_return: bool = False,
    ) -> ChatResult:
        """
        Сгенерировать приветствие от персонажа.

        Args:
            telegram_id: Telegram user ID
            persona_id: ID персонажа
            story_id: ID истории/сценария
            atmosphere: Атмосфера
            is_return: Это возврат к диалогу?

        Returns:
            ChatResult с приветствием
        """
        user = await self.get_user(telegram_id)
        if not user:
            return ChatResult(success=False, error="User not found")

        persona = await self.get_persona(persona_id)
        if not persona:
            return ChatResult(success=False, error="Persona not found")

        # Получаем или создаём диалог
        dialog = await self.get_or_create_dialog(
            user=user,
            persona_id=persona_id,
            story_id=story_id,
            atmosphere=atmosphere,
        )

        # Загружаем историю если это возврат
        prompt_messages = []
        if is_return and dialog.message_count and dialog.message_count > 0:
            recent_messages = await self.get_recent_messages(dialog.id)
            prompt_messages = [
                PromptMessage(role=m.role, content=m.content)
                for m in recent_messages[-4:]  # Берём только 4 последних для контекста
            ]

        # Режим приветствия
        mode = "greeting_return" if is_return else "greeting_first"

        # Строим контекст
        ctx = ChatPromptContext(
            persona_key=persona.key,
            user_name=user.first_name,
            mode=mode,
            atmosphere=atmosphere or dialog.atmosphere,
            story_key=story_id or dialog.story_id,
            recent_messages=prompt_messages,
        )

        # Строим сообщения (без user message - персонаж начинает)
        messages = build_chat_messages(ctx, None)

        # Добавляем инструкцию для начала диалога
        if mode == "greeting_first":
            messages.append({
                "role": "user",
                "content": "[Пользователь открыл диалог. Поприветствуй его первой, представься и начни разговор.]"
            })
        else:
            messages.append({
                "role": "user",
                "content": "[Пользователь вернулся к диалогу. Вспомни о чём вы говорили и продолжи.]"
            })

        # Отправляем в LLM
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.9,
            max_tokens=512,
        )

        if not response:
            return ChatResult(
                success=False,
                error="LLM Gateway error",
                dialog_id=dialog.id,
            )

        # Сохраняем приветствие
        await self.save_message(dialog, "assistant", response)
        await self.db.commit()

        return ChatResult(
            success=True,
            response=response,
            dialog_id=dialog.id,
            message_count=dialog.message_count or 0,
        )


async def process_chat_message(
    db: AsyncSession,
    telegram_id: int,
    message: str,
    persona_id: Optional[int] = None,
    mode: str = "default",
    story_id: Optional[str] = None,
    atmosphere: Optional[str] = None,
) -> ChatResult:
    """
    Удобная функция для обработки сообщения.

    Args:
        db: AsyncSession
        telegram_id: Telegram user ID
        message: Текст сообщения
        persona_id: ID персонажа
        mode: Режим диалога
        story_id: ID истории
        atmosphere: Атмосфера

    Returns:
        ChatResult
    """
    flow = ChatFlow(db)
    return await flow.process_message(
        telegram_id=telegram_id,
        user_message=message,
        persona_id=persona_id,
        mode=mode,
        story_id=story_id,
        atmosphere=atmosphere,
    )


async def generate_persona_greeting(
    db: AsyncSession,
    telegram_id: int,
    persona_id: int,
    story_id: Optional[str] = None,
    atmosphere: Optional[str] = None,
    is_return: bool = False,
) -> ChatResult:
    """
    Удобная функция для генерации приветствия.

    Args:
        db: AsyncSession
        telegram_id: Telegram user ID
        persona_id: ID персонажа
        story_id: ID истории
        atmosphere: Атмосфера
        is_return: Возврат к диалогу?

    Returns:
        ChatResult
    """
    flow = ChatFlow(db)
    return await flow.generate_greeting(
        telegram_id=telegram_id,
        persona_id=persona_id,
        story_id=story_id,
        atmosphere=atmosphere,
        is_return=is_return,
    )


__all__ = [
    "ChatResult",
    "ChatFlow",
    "process_chat_message",
    "generate_persona_greeting",
]
