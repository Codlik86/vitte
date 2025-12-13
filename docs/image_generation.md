# Генерация изображений через ComfyUI (SDXL + LoRA)

## Как это работает
- После того как бот отправил текстовый ответ, в фоне пытается запустить `services.image_generation.maybe_generate_and_send_image`.
- Счётчик `users.bot_reply_counter` увеличивается при каждой реплике ассистента; на кратных `IMAGE_EVERY_N_BOT_REPLIES` и при прохождении `IMAGE_COOLDOWN_SECONDS` создаётся задача генерации.
- Перед запросом проверяются квоты (`image_quota` + подписка), ставится `last_image_sent_at`, логируется `image_requested`, далее запрос уходит на ComfyUI. Ошибка/отсутствие GPU не блокирует чат.
- Успешная генерация пишет `image_generated`, списывает квоту (`consume_image`), отправляет фото в Telegram. Ошибки — `image_failed` с reason.

## Настройки окружения
Добавлены переменные в `.env`:
- `COMFYUI_BASE_URL` — `http://GPU_HOST:8188`
- `COMFYUI_TIMEOUT_SECONDS` — общий таймаут ожидания истории/скачивания (по умолчанию 120)
- `COMFYUI_CONCURRENCY` — максимум одновременных генераций на процесс (по умолчанию 2)
- `COMFYUI_DEFAULT_CHECKPOINT` — имя чекпоинта в ComfyUI (например `sd_xl_base_1.0.safetensors`)
- `IMAGE_EVERY_N_BOT_REPLIES` — частота картинок (default 3)
- `IMAGE_COOLDOWN_SECONDS` — минимальный интервал между попытками (default 120)
- `IMAGE_ENABLED` — быстрый выключатель фичи

## Настройка персонажей и LoRA
- Конфиг находится в `backend/app/services/persona_images.py`.
- Для каждого персонажа можно задать:
  - `lora_filename` (путь относительно `ComfyUI/models/lora/`)
  - `lora_strength_model` / `lora_strength_clip`
  - `prompt_core` — жёсткое ядро промпта
  - `negative_prompt` — базовый негатив
  - `default_style` — необязательная сцена/освещение
- Поиск идёт по `persona.key` или `persona.name` в нижнем регистре, иначе берётся `DEFAULT_IMAGE_CONFIG`.
- Чтобы добавить персонажа: добавить LoRA в ComfyUI, прописать новый ключ в `PERSONA_IMAGE_CONFIGS`, при необходимости поправить `prompt_core`.

## Шаблон ComfyUI
- Хранится в `backend/app/assets/comfyui/workflows/sdxl_lora.json`.
- Схема: `CheckpointLoaderSimple` → `LoraLoader` → `CLIPTextEncode (±)` → `EmptyLatentImage` → `KSampler` → `VAEDecode` → `SaveImage`.
- Код подставляет чекпоинт, LoRA, веса, тексты промптов и сид перед отправкой в `/prompt`.

## Поток работы
1. `chat_flow.generate_chat_reply` увеличивает `bot_reply_counter`.
2. Бот (aiogram) после отправки текста дергает `maybe_generate_and_send_image` (только в приватных чатах).
3. Фоновая задача проверяет `IMAGE_EVERY_N_BOT_REPLIES`, `IMAGE_COOLDOWN_SECONDS`, наличие квоты/подписки, логирует `image_requested`.
4. Через HTTP (aiohttp/httpx) вызывается ComfyUI: POST `/prompt`, опрос `/history/{prompt_id}`, скачивание `/view`.
5. Успех → `consume_image`, `image_generated`, отправка фото. Ошибки → `image_failed`, текст остаётся без изменений.

## Диагностика
- Логи: ищите `image_requested`, `image_generated`, `image_failed` в `events_analytics` и stdout.
- Типовые проблемы:
  - `COMFYUI_BASE_URL` пуст или недоступен → генерация пропускается.
  - Нет квоты (`image_failed reason=no_quota`).
  - Таймаут/ошибка ComfyUI (`generation_error`).
  - Ошибка доставки в Telegram (`send_error`).
- Проверить работу ComfyUI вручную:
  1) `curl -X POST $COMFYUI_BASE_URL/prompt -H 'Content-Type: application/json' -d @backend/app/assets/comfyui/workflows/sdxl_lora.json`
  2) Проверить `/history/{prompt_id}` до появления `images`.
  3) Скачать файл через `/view?filename=...`.

## Ручной чеклист
1. Запустить ComfyUI на GPU, скопировать SDXL чекпоинт в `models/checkpoints`, LoRA файлы в `models/lora`.
2. Прописать env: `COMFYUI_BASE_URL`, `COMFYUI_DEFAULT_CHECKPOINT`, при необходимости скорректировать `IMAGE_*`.
3. Запустить backend, отправить 3 сообщения в приватный чат бота → на третье сообщение должна прийти картинка (если квоты и cooldown позволяют).
4. Проверить, что при отключенном `IMAGE_ENABLED=false` текстовые ответы отправляются без ошибок.
