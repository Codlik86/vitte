# Image Generation Integration

Интеграция NSFW генерации изображений через ComfyUI в ChatFlow.

## Что сделано

### 1. Инфраструктура
- ✅ Создан image-generator microservice с Celery workers (concurrency=2)
- ✅ Redis DB isolation: image-generator использует DB 3/4 (worker использует DB 1/2)
- ✅ ComfyUI pool manager с worker affinity (Worker 0 → 8188, Worker 1 → 8189)
- ✅ Поддержка 2 параллельных ComfyUI инстансов на GPU

### 2. Workflow маппинг
- ✅ 8 персон с готовыми workflows (ASH, JULIE, LINA, MARRIANA, MAY, STACY, TAYA, UNA)
- ✅ Workflows в формате ComfyUI API JSON
- ✅ Z-Image Turbo с FP8 quantization

### 3. ChatFlow интеграция
- ✅ Добавлен триггер генерации каждые 3-5 сообщений (random)
- ✅ Использует последнее сообщение пользователя как промт (временно)
- ✅ Отправка задачи через Celery в image-generator queue
- ✅ Tracking последней генерации в `dialog.last_image_generation_at`

## Файлы

### Новые файлы:
1. `services/image-generator/` - весь микросервис
2. `services/bot/api/app/services/image_generation.py` - триггер генерации
3. `services/bot/api/app/utils/celery_client.py` - Celery client для API
4. `migrations/add_image_generation_tracking.sql` - миграция БД

### Измененные файлы:
1. `shared/database/models.py` - добавлено поле `Dialog.last_image_generation_at`
2. `services/bot/api/app/services/chat_flow.py` - добавлен триггер генерации
3. `docker-compose.yml` - добавлен сервис image-generator

## Развертывание

### 1. Миграция БД

```bash
# На CPU сервере
cd /root/vitte_dev_for_deploy/telegram-bot-microservices
docker exec -i vitte_postgres psql -U vitte_user -d vitte_bot < migrations/add_image_generation_tracking.sql
```

### 2. Перезапуск сервисов

```bash
# Пересобрать и запустить image-generator (уже запущен)
docker compose up -d --build image-generator

# Пересобрать API (для новых изменений в chat_flow.py)
docker compose up -d --build api
```

### 3. Проверка

```bash
# Проверить что image-generator работает
docker compose logs image-generator | tail -20

# Проверить что API подключился к Celery
docker compose logs api | grep -i celery
```

## GPU сервер

### ComfyUI инстансы:
- **Порт 8188**: первый инстанс (Worker 0)
- **Порт 8189**: второй инстанс (Worker 1)

### Запуск (уже запущено):
```bash
# Terminal 1
cd /home/ubuntu/ComfyUI
python main.py --listen 0.0.0.0 --port 8188 --highvram --use-sage-attention

# Terminal 2
cd /home/ubuntu/ComfyUI
/home/ubuntu/ComfyUI/venv/bin/python main.py --listen 0.0.0.0 --port 8189 --highvram --use-sage-attention
```

## Архитектура

```
User Message → ChatFlow (API)
                   ↓
        Check message_count % random(3,5)
                   ↓
        Celery Task → Redis DB 3 (broker)
                   ↓
         ┌─────────┴─────────┐
    Worker 0            Worker 1
         ↓                   ↓
   ComfyUI:8188        ComfyUI:8189
         ↓                   ↓
      Generate            Generate
         ↓                   ↓
   Send to Telegram    Send to Telegram
```

## Логика триггера

1. **Частота**: каждые 3-5 сообщений (рандом при каждой проверке)
2. **Промт**: последнее сообщение пользователя (пока)
3. **Seed**: random (None)
4. **Tracking**: `dialog.last_image_generation_at` сохраняет message_count последней генерации
5. **Refresh**: не триггерит генерацию (только в `process_message()`)

## Следующие шаги (TODO)

1. **Prompt Builder**: создать промт билдеры для каждой персоны
   - Должен учитывать вывод LLM
   - Генерировать NSFW промт на основе контекста диалога
   - Адаптировать под стиль каждой персоны

2. **Fixed Seed**: для воспроизводимости и кеширования
   - Seed на основе dialog_id + message_count
   - Кеш сгенерированных изображений

3. **Дефолтные картинки**: на старте диалога (уже есть)

4. **Мониторинг**:
   - Метрики генерации (время, ошибки)
   - Queue depth (Celery)
   - GPU utilization

## Конфигурация

### Environment Variables:

```bash
# image-generator service
COMFYUI_HOSTS=195.209.210.175:8188,195.209.210.175:8189
IMAGE_GENERATION_FREQUENCY=4  # Not used (random 3-5)
MAX_CONCURRENT_GENERATIONS=2
GENERATION_TIMEOUT=120
REDIS_BROKER_DB=3
REDIS_RESULT_DB=4
```

### API service:

```bash
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

## Проблемы и решения

### 1. Redis DB isolation
**Проблема**: Worker и image-generator использовали одни и те же Redis DBs
**Решение**: image-generator → DB 3/4, worker → DB 1/2

### 2. Password encoding
**Проблема**: Спецсимволы (!, #) в Redis пароле
**Решение**: URL encoding через `quote_plus()`

### 3. SystemD конфликт
**Проблема**: `comfyui.service` автозапускался и занимал порт 8188
**Решение**: `sudo systemctl disable comfyui.service`

## Logs

### Успешная генерация:
```
[INFO] Using ComfyUI instance: http://195.209.210.175:8188
[INFO] Starting generation on http://195.209.210.175:8188
[INFO] Queued prompt with ID: abc-123-def
[INFO] Generation abc-123-def completed
[INFO] Image generated successfully, size: 1234567 bytes
[INFO] Image sent successfully to chat 123456789
```

### Триггер в ChatFlow:
```
[INFO] Image generation triggered for dialog 42, persona=lina, message_count=5, task_id=xyz-789
```
