# Vitte Architecture Review (Image + Text)

## Entry Points
- `backend/app/api/routes_webhook.py:telegram_webhook` → `bot.handle_update` → aiogram Dispatcher.
- Handlers: `bot.on_user_message`, `bot.on_image_requested`, pay callbacks.

## Text Reply Pipeline
- `on_user_message` → `chat_flow.generate_chat_reply`.
- Context: persona, dialog/history (`messages`), story (`story_cards` via `Dialog.entry_story_id`), relationship state (`relationship_states`), safety/intimacy, features.
- Prompt: `prompt_builder.build_chat_messages` (persona, safety, mode, story, recent dialogue, memory, relationship block, features) + user message.
- LLM: `integrations.llm_client.simple_chat_completion`.
- Persist: messages, counters, relationship state (unless test mode).

## Image Pipeline
- Trigger: inline button “👁️ Посмотреть” (`bot.on_image_requested`).
- Lock/quota: advisory lock on (user, persona), `image_quota` check.
- Context: dialog, story (entry_story_id → `story_cards`), last user messages, optional history, persona config (`persona_images`).
- Hint: story + user_request/history (currently mixed), prompt_core + negative from persona_images.
- ComfyUI: workflow bolванка `assets/comfyui/workflows/sdxl_lora.json`, nodes by class_type, HTTP `/prompt` → `/history/{id}` → `/view`.
- Persist image usage: `image_generated` event, `consume_image`, `last_image_sent_at`.

## Where Responsibilities Mix / Risks
- `image_generation._build_prompt_hint` смешивает story/history/reply/persona; user intent может теряться при обрезке.
- `prompt_builder` + `llm_adapter` вставляют сложный trust ladder; отношения управляются тремя метриками (trust/respect/closeness) → сложно администрировать.
- Реплики “leggings/одежда” возможны из persona/story/memory повторов; нет анти-повтора.
- Advisory lock и квоты реализованы, но prompt сборка для изображений неструктурирована.

## Key Files
- `bot.py`: handlers, safe callback answers, image button.
- `chat_flow.py`: диалог, история, story, отношения, safety, LLM вызов.
- `prompt_builder.py`: system prompt blocks.
- `llm_adapter.py`: trust ladder, mode descriptions.
- `relationship_state.py`: таблица relationship_states, trust/respect/closeness.
- `image_generation.py`: hint сбор, ComfyUI запросы, квоты, lock.
- `persona_images.py`: LoRA prompt_core/negative, (нужно держать без окружений).
- `story_cards.py`: сцены и сеттинги.
- `image_quota.py`: квоты изображений.
- `models.py`: ORM схемы.

## Problems to Fix
- Image prompt: отсутствие жёсткого приоритета user intent > story scene > semantic > fallback; нужен структурированный формат.
- Trust/relationship: усложнённая лестница; нет 3 простых уровней с управляемостью.
- Анти-повтор: нет guard от фиксации на одежде/предметах.
- Документация по pipeline отсутствует.
