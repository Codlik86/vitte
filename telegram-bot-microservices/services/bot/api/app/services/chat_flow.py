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
import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import User, Dialog, Message, Persona, FeatureUnlock, Subscription
from shared.database.image_service import get_images_remaining, use_image_quota
from shared.llm.services.safety import run_safety_check, get_supportive_reply
from shared.llm.services.intimacy import get_intimacy_instruction
from shared.llm.services.prompt_builder import (
    ChatPromptContext,
    Message as PromptMessage,
    build_chat_messages,
)
from shared.utils import redis_client

from celery.result import AsyncResult

from shared.llm.services.image_prompt_builder import (
    build_image_prompt_messages,
    assemble_final_prompt,
    get_story_seed,
)
from shared.llm.services.sex_images import (
    has_sex_images,
    get_sex_image_url,
    should_send_sex_image,
    SCENE_MAP,
)
from shared.llm.services.sex_scene_detector import detect_sex_scene

from .llm_client import llm_client
from .embedding_service import embedding_service
from .image_generation import ImageGenerationService
from app.utils.celery_client import celery_app

logger = logging.getLogger(__name__)
debug_logger = logging.getLogger('uvicorn.error')  # Для debug-логов которые точно выведутся

MAX_DIALOG_SLOTS = 10
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
    image_url: Optional[str] = None  # URL сгенерированного изображения
    no_image_quota: bool = False  # True when image was due but user has no quota


def _remove_duplicate_sentences(text: str) -> str:
    """
    Удаляет повторяющиеся предложения из ответа LLM.

    Используется post-processing подход (industry standard для Character AI).
    Источник: https://milvus.io/ai-quick-reference
    """
    if not text or len(text) < 50:
        return text

    # Разбиваем на предложения (по точкам, вопросам, восклицаниям)
    sentences = re.split(r'([.!?]\s+)', text)

    # Собираем обратно с разделителями
    parts = []
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i].strip()
            separator = sentences[i + 1] if i + 1 < len(sentences) else ''

            if sentence:
                parts.append((sentence, separator))

    # Удаляем дубликаты, сохраняя порядок
    seen = set()
    unique_parts = []

    for sentence, separator in parts:
        # Нормализуем для сравнения (убираем ремарки и лишние пробелы)
        normalized = re.sub(r'\*[^*]+\*', '', sentence).strip().lower()

        if normalized and normalized not in seen and len(normalized) > 10:
            seen.add(normalized)
            unique_parts.append(sentence + separator)

    result = ''.join(unique_parts).strip()

    # Логируем если были удалены дубли
    if len(unique_parts) < len(parts):
        removed_count = len(parts) - len(unique_parts)
        logger.warning(f"Post-processing: removed {removed_count} duplicate sentence(s)")

    return result


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
        # Ищем существующий активный диалог с этим персонажем И этой историей
        query = select(Dialog).where(
            and_(
                Dialog.user_id == user.id,
                Dialog.persona_id == persona_id,
                Dialog.is_active == True,
            )
        )
        if story_id:
            query = query.where(Dialog.story_id == story_id)

        result = await self.db.execute(query)
        dialog = result.scalar_one_or_none()

        if dialog:
            # Обновляем atmosphere если изменилась
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

        # 2.5. Check message limit (free users: 20/day)
        try:
            sub_result = await self.db.execute(
                select(Subscription).where(Subscription.user_id == telegram_id)
            )
            subscription = sub_result.scalar_one_or_none()
            has_active_sub = False
            if subscription and subscription.is_active:
                now = datetime.utcnow()
                if subscription.expires_at and subscription.expires_at > now:
                    has_active_sub = True

            if not has_active_sub:
                # Free user - check daily limit via Redis
                redis_key = f"user:{telegram_id}:messages:daily"
                current_count = await redis_client.get(redis_key)
                if current_count is not None and int(current_count) >= 20:
                    return ChatResult(
                        success=False,
                        error="Дневной лимит сообщений исчерпан (20/день). Оформите подписку для безлимитного общения.",
                    )
                # Increment counter
                if current_count is None:
                    now = datetime.utcnow()
                    midnight = datetime(now.year, now.month, now.day, 23, 59, 59)
                    seconds_until_midnight = int((midnight - now).total_seconds()) + 1
                    await redis_client.set(redis_key, "1", expire=seconds_until_midnight)
                else:
                    await redis_client.increment(redis_key)
        except Exception as e:
            debug_logger.warning(f"Message limit check error (allowing): {e}")

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

        # DEDUPLICATION: Удаляем последовательные дубликаты (когда assistant отвечает одно и то же подряд)
        deduped_messages = []
        prev_content = None
        for m in recent_messages:
            # Если это assistant и контент совпадает с предыдущим assistant - пропускаем
            if m.role == "assistant" and m.content == prev_content:
                debug_logger.warning(f"Skipping duplicate assistant message: {m.content[:100]}")
                continue
            deduped_messages.append(m)
            if m.role == "assistant":
                prev_content = m.content
            else:
                prev_content = None  # Сбрасываем если это user message

        prompt_messages = [
            PromptMessage(role=m.role, content=m.content)
            for m in deduped_messages
        ]
        # DEBUG: Логируем историю сообщений
        debug_logger.warning(f"Recent messages count: {len(recent_messages)} -> after dedup: {len(deduped_messages)}")
        debug_logger.warning(f"Recent messages: {[(m.role, m.content[:100]) for m in deduped_messages]}")

        # 6. Поиск релевантных воспоминаний из Qdrant
        memory_long = None
        if dialog.message_count and dialog.message_count > 5:
            memories = await embedding_service.search_memories(
                user_id=telegram_id,
                persona_id=persona_id,
                query=user_message,
                limit=3,
            )
            # DEBUG: Логируем что вернул Qdrant
            debug_logger.warning(f"Qdrant memories for user {telegram_id}: {len(memories) if memories else 0} items")
            if memories:
                debug_logger.warning(f"Qdrant memories content: {memories}")
                memory_parts = []
                for m in memories:
                    role_label = "Ты" if m["role"] == "assistant" else "Пользователь"
                    memory_parts.append(f"- {role_label}: {m['text'][:200]}")
                memory_long = "\n".join(memory_parts)
                debug_logger.warning(f"Memory_long built: {memory_long}")

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
        debug_logger.warning(f"\n\n{'='*80}\nSYSTEM PROMPT for {persona.key} (user {telegram_id})\n{'='*80}\n{system_prompt}\n{'='*80}\nUser message: {user_message}\nAllow intimate: {allow_intimate}, Has features: {has_intense_mode or has_fantasy_scenes}\n{'='*80}\n")

        # DEBUG: Логируем все messages которые отправляются в LLM
        debug_logger.warning(f"\n\n{'='*80}\nFULL MESSAGES ARRAY TO LLM ({len(messages)} messages)\n{'='*80}")
        for idx, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            content_preview = content[:200] + "..." if len(content) > 200 else content
            debug_logger.warning(f"Message {idx}: [{role}] {content_preview}")
        debug_logger.warning(f"{'='*80}\n")

        # 9.5. Image: ONE trigger → decide sex pool OR ComfyUI
        import asyncio
        from sqlalchemy.orm.attributes import flag_modified
        image_url = None
        image_celery_task = None
        sex_image_from_pool = False
        no_quota_flag = False
        try:
            service = ImageGenerationService(celery_app)
            current_count = (dialog.message_count or 0) + 2
            should_generate = service.should_generate_image(
                message_count=current_count,
                last_generation_at=dialog.last_image_generation_at
            )
            assistant_count = (current_count + 1) // 2
            debug_logger.warning(f"IMG: dialog={dialog.id}, msg_count={dialog.message_count}, current_count={current_count}, assistant_count={assistant_count}, should_generate={should_generate}")

            if should_generate:
                # Single decision point: sex pool or ComfyUI?
                use_sex_pool = False

                # Run detect_sex_scene and build_image_prompt in parallel
                recent_for_detection = [
                    {"role": m.role, "content": m.content}
                    for m in deduped_messages[-4:]
                ]
                recent_for_detection.append({"role": "user", "content": user_message})

                img_recent = [
                    {"role": m.role, "content": m.content}
                    for m in deduped_messages[-4:]
                ]
                img_messages = build_image_prompt_messages(
                    persona_key=persona.key,
                    story_key=story_id or dialog.story_id,
                    user_message=user_message,
                    recent_messages=img_recent,
                )

                async def _detect_scene():
                    try:
                        result = await detect_sex_scene(recent_for_detection, llm_client)
                        debug_logger.warning(f"IMG: detected scene={result}")
                        return result
                    except Exception as e:
                        debug_logger.warning(f"IMG: scene detection error: {e}", exc_info=True)
                        return None

                async def _build_prompt():
                    try:
                        raw = await llm_client.chat_completion(
                            messages=img_messages,
                            temperature=0.7,
                            max_tokens=120,
                        )
                        if raw:
                            result = assemble_final_prompt(persona.key, raw)
                            debug_logger.warning(f"IMG PROMPT: {result}")
                            return result
                        debug_logger.warning(f"IMG PROMPT: LLM returned None, using fallback")
                        return None
                    except Exception as e:
                        debug_logger.warning(f"IMG PROMPT ERROR: {e}")
                        return None

                scene_name, comfy_prompt = await asyncio.gather(_detect_scene(), _build_prompt())

                if not comfy_prompt:
                    from shared.llm.services.image_prompt_builder import PERSONA_TRIGGER_WORDS
                    tw = PERSONA_TRIGGER_WORDS.get(persona.key, "")
                    comfy_prompt = f"{tw}, a beautiful woman, soft lighting, realistic photography" if tw else "a beautiful woman, soft lighting, realistic photography"

                # Sex pool only after 9th assistant message
                if assistant_count >= 9 and has_sex_images(persona.key) and scene_name and scene_name != "nude":
                    debug_logger.warning(f"IMG: sex pose detected, checking pool for persona={persona.key}, story={story_id or dialog.story_id}")
                    try:
                        indices = dialog.sex_scene_indices or {}
                        schene_key = f"schene_{SCENE_MAP[scene_name]}"
                        current_index = indices.get(schene_key, 0)

                        sex_url = get_sex_image_url(
                            persona_key=persona.key,
                            story_key=story_id or dialog.story_id,
                            scene_name=scene_name,
                            index=current_index,
                        )
                        debug_logger.warning(f"IMG: sex pool url={sex_url}, scene={scene_name}, index={current_index}")

                        if sex_url:
                            image_url = sex_url
                            sex_image_from_pool = True
                            use_sex_pool = True
                            indices[schene_key] = current_index + 1
                            dialog.sex_scene_indices = indices
                            flag_modified(dialog, "sex_scene_indices")
                            dialog.last_image_generation_at = current_count
                            debug_logger.warning(f"IMG: using sex pool, next_index={current_index + 1}")
                    except Exception as sex_err:
                        debug_logger.warning(f"IMG: sex pool error: {sex_err}", exc_info=True)

                if not use_sex_pool:
                    # Check if nude context → use Moody model
                    use_moody = False
                    if scene_name == "nude":
                        use_moody = True
                        debug_logger.warning(f"IMG: nude context detected → using Moody model")

                    # Not sex pool → ComfyUI generation (ZIT or Moody)
                    image_quota = await get_images_remaining(self.db, telegram_id)
                    debug_logger.warning(f"IMG: ComfyUI path (moody={use_moody}), quota: can={image_quota.can_generate}, remaining={image_quota.total_remaining}")

                    if image_quota.can_generate:
                        story_seed = get_story_seed(persona.key, story_id or dialog.story_id)
                        model_override = 2 if use_moody else None
                        image_celery_task = celery_app.send_task(
                            'image_generator.generate_image',
                            args=[persona.key, comfy_prompt, story_seed, model_override],
                            queue='image_generation',
                        )
                        dialog.last_image_generation_at = current_count
                        debug_logger.warning(f"IMG: started ComfyUI task_id={image_celery_task.id}, model={'moody' if use_moody else 'zit'}")
                    else:
                        no_quota_flag = True
                        debug_logger.warning(f"IMG: skipped - no image quota remaining")
        except Exception as e:
            debug_logger.warning(f"IMG ERROR: {e}", exc_info=True)

        # 10. Отправляем в LLM Gateway (runs parallel with ComfyUI if triggered)
        response = await llm_client.chat_completion(
            messages=messages,
            temperature=0.85,
            max_tokens=600,
            presence_penalty=0.3,
            frequency_penalty=0.4,
        )

        # DEBUG: Логируем ответ LLM
        debug_logger.warning(f"\n\n{'='*80}\nLLM RESPONSE for {persona.key}\n{'='*80}\n{response}\n{'='*80}\n")

        # 11. Post-processing: удаляем повторяющиеся предложения внутри ответа
        if response:
            response = _remove_duplicate_sentences(response)

        if not response:
            return ChatResult(
                success=False,
                error="LLM Gateway error",
                dialog_id=dialog.id,
            )

        # 11.5. Wait for ComfyUI image generation result (up to 90 sec)
        # Skip if sex pool image was already set (no ComfyUI task)
        if image_celery_task:
            try:
                debug_logger.warning(f"IMG: LLM done, waiting for ComfyUI task_id={image_celery_task.id} (max 90s)")
                async_result = AsyncResult(image_celery_task.id, app=celery_app)
                result_data = await asyncio.to_thread(
                    async_result.get, timeout=90, propagate=False
                )
                if result_data and isinstance(result_data, dict) and result_data.get('success'):
                    image_url = result_data.get('image_url')
                    # Deduct 1 image from quota (only for ComfyUI, not sex pool)
                    quota_result = await use_image_quota(self.db, telegram_id)
                    debug_logger.warning(f"IMG: got image: {image_url}, deducted from={quota_result.source}, remaining={quota_result.total_remaining}")
                else:
                    debug_logger.warning(f"IMG: generation failed or bad result: {result_data}")
            except Exception as e:
                debug_logger.warning(f"IMG: timeout/error waiting for ComfyUI: {e}")

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

        # 14. Коммитим изменения
        await self.db.commit()

        return ChatResult(
            success=True,
            response=response,
            dialog_id=dialog.id,
            image_url=image_url,  # Include generated image URL
            message_count=dialog.message_count or 0,
            no_image_quota=no_quota_flag,
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
            max_tokens=600,
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
