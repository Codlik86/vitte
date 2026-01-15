# FRONTEND_PRESENT: Проблемы и уязвимости старого проекта

> Технический анализ слабых сторон LLM интеграции, безопасности и архитектуры

---

## 1. LLM Context Management

### Проблемы

| Проблема | Где | Влияние |
|----------|-----|---------|
| Лимит 12 сообщений | `chat_flow.py` → `get_recent_messages()` | Потеря контекста в длинных диалогах |
| Нет chunking | Ответы LLM обрезаются | Неполные ответы пользователю |
| Long-term memory = None | `memory_block` всегда пустой | Персонаж "забывает" важные факты о пользователе |
| Нет summarization | Старые сообщения удаляются | Невозможно вспомнить начало разговора |

### Код проблемы

```python
# Текущая реализация - жёсткий лимит
messages = await get_recent_messages(db, user_id, limit=12)

# memory_block не используется
memory_block = ""  # TODO: implement long-term memory
```

### Решение

- Реализовать sliding window с summarization старых сообщений
- Добавить RAG для long-term memory (важные факты о пользователе)
- Chunking для длинных ответов с продолжением

---

## 2. Безопасность

### 2.1 Pattern-based Safety Filter

**Проблема:** Regex паттерны легко обойти

```python
# Текущий подход
UNSAFE_PATTERNS = [
    r"несовершеннолетн",
    r"ребенок",
    r"детск",
    # ...
]
```

**Обход:**
- `р е б ё н о к` (пробелы)
- `peбeнok` (латиница)
- `child` (английский)

**Решение:** LLM-based moderation (OpenAI Moderation API или custom classifier)

### 2.2 Intimacy Gate на фронтенде

**Проблема:** Проверка подписки только в Web App

```typescript
// frontend/src/components/Chat.tsx
if (!user.hasIntimateAccess && isIntimateContent) {
  showPaywall();
}
```

**Обход:** Прямой запрос к API минуя фронтенд

**Решение:** Проверка подписки на бэкенде перед генерацией контента

### 2.3 Нет Rate Limiting на LLM

**Проблема:** Один пользователь может спамить запросами

**Влияние:**
- Исчерпание бюджета API
- DoS других пользователей

**Решение:**
- Redis-based rate limiter
- Лимиты по подписке (Free: 10 req/min, Premium: 60 req/min)

---

## 3. Производительность

### 3.1 Синхронные вызовы без streaming

**Проблема:** Пользователь ждёт полный ответ

```python
# Текущий подход - блокирующий вызов
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    # stream=False (по умолчанию)
)
```

**Влияние:**
- UX: 5-15 секунд ожидания без фидбека
- Timeout errors на длинных ответах

**Решение:**

```python
# Streaming
async for chunk in await client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=True
):
    await send_typing_action()
    yield chunk.choices[0].delta.content
```

### 3.2 Нет кеширования System Prompts

**Проблема:** Промпт пересобирается при каждом запросе

```python
# Каждый раз заново
system_prompt = build_system_prompt(
    persona=persona,
    story=story,
    mode=mode,
    # ... 7 блоков
)
```

**Влияние:**
- CPU overhead
- Невозможно использовать prompt caching провайдера

**Решение:**

```python
# Redis cache с TTL
cache_key = f"prompt:{persona_id}:{story_id}:{mode}"
cached = await redis.get(cache_key)
if not cached:
    prompt = build_system_prompt(...)
    await redis.setex(cache_key, 3600, prompt)
```

### 3.3 Избыточная загрузка сообщений

**Проблема:** Полная загрузка при каждом запросе

```python
# Загружаем ВСЕ поля каждый раз
messages = await db.query(Message).filter(...).all()
```

**Решение:**
- Lazy loading
- Кеширование последних N сообщений в Redis
- Projection (только нужные поля)

---

## 4. Архитектура

### 4.1 Tight Coupling в chat_flow.py

**Проблема:** Один файл 500+ строк со всей логикой

```
chat_flow.py
├── LLM calls
├── Safety checks
├── Persona loading
├── Story management
├── Message history
├── Image generation
├── Payment checks
└── Error handling
```

**Решение:** Разделение на сервисы

```
services/
├── llm_service.py      # LLM вызовы
├── safety_service.py   # Модерация
├── persona_service.py  # Персонажи
├── memory_service.py   # История/контекст
└── media_service.py    # Генерация изображений
```

### 4.2 Нет Retry Queue

**Проблема:** Failed LLM calls теряются

```python
try:
    response = await llm_call()
except Exception:
    await message.answer("Ошибка, попробуйте позже")
    # Запрос потерян
```

**Решение:**

```python
# Redis queue с retry
await retry_queue.add(
    task="llm_call",
    payload={"user_id": user_id, "message": text},
    max_retries=3,
    backoff="exponential"
)
```

### 4.3 Валидация после LLM

**Проблема:** Проверка русского языка после генерации

```python
response = await llm_generate()  # Потратили токены
if not is_russian(response):     # Только потом проверяем
    response = await regenerate() # Тратим ещё токены
```

**Решение:** Усилить system prompt + добавить language constraint в parameters

---

## 5. Масштабируемость

### 5.1 In-memory Locale Cache

**Проблема:** Кеш локали в памяти процесса

```python
_locale_cache: Dict[int, str] = {}
```

**Влияние:** При multi-instance (k8s, docker swarm) кеши рассинхронизированы

**Решение:** Redis для shared state

```python
async def get_locale(user_id: int) -> str:
    return await redis.get(f"locale:{user_id}") or "ru"
```

### 5.2 Image Generation Blocking

**Проблема:** Генерация изображений блокирует воркер

```python
# Синхронная генерация
image = await generate_image(prompt)  # 10-30 сек
await message.answer_photo(image)
```

**Влияние:** Один запрос на картинку блокирует обработку других сообщений

**Решение:**

```python
# Async job queue (Celery/ARQ)
job_id = await image_queue.enqueue(
    "generate_image",
    prompt=prompt,
    user_id=user_id
)
await message.answer("🎨 Генерирую изображение...")
# Webhook при готовности
```

### 5.3 Нет Connection Pooling

**Проблема:** Новое соединение на каждый LLM запрос

**Решение:**

```python
# httpx с connection pool
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    )
)
```

---

## 6. Quick Wins (быстрые улучшения)

| # | Задача | Сложность | Влияние |
|---|--------|-----------|---------|
| 1 | LLM Streaming | Средняя | Высокое - UX |
| 2 | Redis locale cache | Низкая | Среднее - масштабирование |
| 3 | Safety в middleware | Средняя | Высокое - безопасность |
| 4 | System prompt cache | Низкая | Среднее - производительность |
| 5 | Rate limiting | Низкая | Высокое - защита от abuse |
| 6 | Backend intimacy check | Низкая | Критичное - безопасность |

---

## Приоритеты исправления

### 🔴 Критичные 
1. Intimacy gate на бэкенде
2. Rate limiting на LLM
3. Connection pooling

### 🟡 Важные 
4. LLM streaming
5. Safety middleware
6. Redis caches

### 🟢 Улучшения
7. Long-term memory
8. Retry queue
9. Service decomposition
