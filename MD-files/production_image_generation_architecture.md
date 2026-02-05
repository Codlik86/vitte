# Production архитектуры для параллельной генерации изображений

## Содержание
- [Ключевые факты о ComfyUI](#ключевые-факты-о-comfyui)
- [Варианты архитектур](#варианты-архитектур)
- [Системы очередей](#системы-очередей)
- [Рекомендуемая архитектура](#рекомендуемая-архитектура)
- [Примеры кода](#примеры-кода)
- [FAQ](#faq)

---

## Ключевые факты о ComfyUI

### Последовательная обработка

ComfyUI обрабатывает запросы **последовательно** — это by design. Одна инстанция = одна очередь.

> Если 30 запросов приходят одновременно, 30-й запрос будет ждать ~30 секунд (при генерации 1 сек/изображение)

### Проблема с несколькими инстанциями на одной GPU

При запуске нескольких ComfyUI серверов на одной GPU:
- Каждый сервер загружает модели **независимо**
- Модели **дублируются в VRAM**
- На GPU с 48GB можно запустить 2-3 инстанции, но VRAM расходуется неэффективно

---

## Варианты архитектур

### Вариант 1: Одна GPU + очередь задач (базовый)

**Подходит для:** небольшого числа пользователей, генерация 2-4 сек

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│   Redis     │────▶│   Worker    │────▶│  ComfyUI    │
│     Bot     │     │   Queue     │     │  (Celery)   │     │    API      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Преимущества:**
- Простая реализация
- Надежная очередь
- Легко мониторить

**Недостатки:**
- Нет параллелизма
- Время ожидания растет линейно с очередью

---

### Вариант 2: Несколько ComfyUI инстанций + Load Balancer

**Подходит для:** GPU с большим VRAM (24GB+), легкие модели

```
                              ┌─────────────┐
                         ┌───▶│  ComfyUI-1  │
┌─────────────┐          │    │  :8188      │
│   Worker    │──────────┤    └─────────────┘
│   Pool      │          │    ┌─────────────┐
└─────────────┘          └───▶│  ComfyUI-2  │
                              │  :8189      │
                              └─────────────┘
```

**Расчет VRAM:**
| Модель | VRAM на инстанцию | Макс. инстанций (24GB) |
|--------|-------------------|------------------------|
| SD 1.5 | ~4GB | 4-5 |
| SDXL | ~8-10GB | 2 |
| Flux | ~12-16GB | 1 |

**Преимущества:**
- Реальный параллелизм
- Увеличение throughput в N раз

**Недостатки:**
- Дублирование моделей в VRAM
- Сложнее управлять

---

### Вариант 3: Serverless GPU (RunPod/Modal)

**Подходит для:** непредсказуемая нагрузка, production SaaS

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐
│     Bot     │────▶│   RunPod    │────▶│  Auto-scaling Workers       │
│             │     │   API       │     │  (0 → N GPU instances)      │
└─────────────┘     └─────────────┘     └─────────────────────────────┘
```

**Характеристики RunPod Serverless:**
- Автоскейлинг от 0 до сотен воркеров
- Pay-per-use (посекундная оплата)
- 48% cold starts под 200ms
- Cold start для больших контейнеров: 6-12 секунд

**Преимущества:**
- Нет расходов когда idle
- Автоматический скейлинг
- Не нужно управлять инфраструктурой

**Недостатки:**
- Cold start latency
- Дороже при постоянной нагрузке
- Зависимость от провайдера

---

### Вариант 4: Distributed ComfyUI (Multi-GPU)

**Подходит для:** несколько GPU, высокая нагрузка

Используется расширение **ComfyUI-Distributed**:
- Параллельная генерация на нескольких GPU
- Автоматический load balancing
- Поддержка локальных и удаленных воркеров

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   Master    │────▶│          Worker Pool                │
│  ComfyUI    │     │  ┌─────┐  ┌─────┐  ┌─────┐         │
└─────────────┘     │  │GPU-0│  │GPU-1│  │GPU-N│         │
                    │  └─────┘  └─────┘  └─────┘         │
                    └─────────────────────────────────────┘
```

---

## Системы очередей

### Сравнение

| Система | Язык | Лучше для | Особенности |
|---------|------|-----------|-------------|
| **Celery + Redis** | Python | ML jobs, image processing | Стандарт для Python |
| **BullMQ** | Node.js/Python | High concurrency | Concurrency 100+, retries |
| **RabbitMQ** | Any | Microservices, ordering | Feature-complete, надежный |
| **Redis Streams** | Any | Real-time, fast queues | In-memory, очень быстрый |

### Celery (Python)

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost')

@app.task
def generate_image(prompt):
    # Вызов ComfyUI API
    return result
```

**Идеально для:** Image processing, ML model calls, PDF generation

### BullMQ (Node.js)

```javascript
import { Queue, Worker } from 'bullmq';

const queue = new Queue('ImageGeneration');

const worker = new Worker('ImageGeneration', async job => {
    return await generateImage(job.data);
}, { concurrency: 100 });
```

**Идеально для:** High-performance queues, retries, rate limiting

---

## Рекомендуемая архитектура

### Для чаттинг-бота с одной арендованной GPU

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│    Redis    │────▶│   Worker    │────▶│  ComfyUI    │
│     Bot     │     │   (Queue)   │     │  (Python)   │     │    API      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Job Status │     │  Callback   │
                    │   Storage   │     │  to Bot     │
                    └─────────────┘     └─────────────┘
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  comfyui:
    image: your-comfyui-image
    command: python main.py --listen 0.0.0.0 --port 8188
    volumes:
      - ./models:/app/models
      - ./output:/app/output
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8188/system_stats"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: ./worker
    environment:
      - REDIS_URL=redis://redis:6379
      - COMFYUI_URL=http://comfyui:8188
      - BOT_CALLBACK_URL=http://bot:8080/callback
    depends_on:
      redis:
        condition: service_healthy
      comfyui:
        condition: service_healthy
    restart: always

  bot:
    build: ./bot
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy
    ports:
      - "8080:8080"
    restart: always

volumes:
  redis_data:
```

---

## Примеры кода

### Worker с Celery

```python
# worker/tasks.py
import time
import requests
from celery import Celery

app = Celery('tasks', broker='redis://redis:6379')

COMFYUI_URL = 'http://comfyui:8188'

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def generate_image(self, workflow: dict, user_id: str, callback_url: str = None):
    """
    Отправляет workflow в ComfyUI и ждет результат
    """
    try:
        # Отправка prompt в ComfyUI
        response = requests.post(
            f'{COMFYUI_URL}/prompt',
            json={'prompt': workflow},
            timeout=10
        )
        response.raise_for_status()
        prompt_id = response.json()['prompt_id']
        
        # Polling для получения результата
        result = poll_for_result(prompt_id, timeout=120)
        
        # Callback к боту
        if callback_url:
            requests.post(callback_url, json={
                'user_id': user_id,
                'prompt_id': prompt_id,
                'status': 'completed',
                'images': result['images']
            })
        
        return result
        
    except Exception as exc:
        self.retry(exc=exc)


def poll_for_result(prompt_id: str, timeout: int = 120) -> dict:
    """
    Ожидает завершения генерации
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f'{COMFYUI_URL}/history/{prompt_id}')
        history = response.json()
        
        if prompt_id in history:
            status = history[prompt_id].get('status', {})
            if status.get('completed'):
                return extract_images(history[prompt_id])
            if status.get('status_str') == 'error':
                raise Exception(f"Generation failed: {status}")
        
        time.sleep(0.5)
    
    raise TimeoutError(f"Generation timeout after {timeout}s")


def extract_images(history_item: dict) -> dict:
    """
    Извлекает URL изображений из результата
    """
    images = []
    outputs = history_item.get('outputs', {})
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for img in node_output['images']:
                images.append({
                    'filename': img['filename'],
                    'subfolder': img.get('subfolder', ''),
                    'type': img.get('type', 'output'),
                    'url': f"{COMFYUI_URL}/view?filename={img['filename']}&type={img.get('type', 'output')}"
                })
    
    return {'images': images}
```

### Bot интеграция

```python
# bot/main.py
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
import aiohttp
import redis.asyncio as redis
from celery import Celery

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
redis_client = redis.from_url('redis://redis:6379')
celery_app = Celery('tasks', broker='redis://redis:6379')

@dp.message_handler(commands=['generate'])
async def generate_handler(message: types.Message):
    user_id = str(message.from_user.id)
    prompt_text = message.get_args()
    
    if not prompt_text:
        await message.reply("Укажите промпт: /generate ваш промпт")
        return
    
    # Создаем workflow
    workflow = create_workflow(prompt_text)
    
    # Отправляем в очередь
    task = celery_app.send_task(
        'tasks.generate_image',
        args=[workflow, user_id, f'http://bot:8080/callback']
    )
    
    # Сохраняем task_id для отслеживания
    await redis_client.set(f'task:{user_id}', task.id, ex=3600)
    
    # Получаем позицию в очереди
    queue_length = await get_queue_length()
    
    await message.reply(
        f"⏳ Запрос принят!\n"
        f"📍 Позиция в очереди: {queue_length}\n"
        f"⏱ Примерное время: ~{queue_length * 3} сек"
    )


@dp.callback_query_handler(lambda c: c.data == 'check_status')
async def check_status(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    task_id = await redis_client.get(f'task:{user_id}')
    
    if not task_id:
        await callback_query.answer("Нет активных задач")
        return
    
    result = celery_app.AsyncResult(task_id.decode())
    
    if result.ready():
        await callback_query.answer("✅ Готово!")
    else:
        await callback_query.answer("⏳ В обработке...")


# Callback endpoint для получения результатов
from aiohttp import web

async def callback_handler(request):
    data = await request.json()
    user_id = data['user_id']
    images = data.get('images', [])
    
    if images:
        for img in images:
            # Скачиваем и отправляем изображение
            async with aiohttp.ClientSession() as session:
                async with session.get(img['url']) as resp:
                    image_data = await resp.read()
                    
            await bot.send_photo(
                chat_id=user_id,
                photo=InputFile(io.BytesIO(image_data), filename=img['filename']),
                caption="🎨 Ваше изображение готово!"
            )
    
    return web.Response(text='OK')
```

### Load Balancer для нескольких ComfyUI

```python
# worker/comfyui_pool.py
import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ComfyUIInstance:
    url: str
    busy: bool = False
    current_job: Optional[str] = None

class ComfyUIPool:
    def __init__(self, urls: List[str]):
        self.instances = [ComfyUIInstance(url=url) for url in urls]
        self.lock = asyncio.Lock()
    
    async def get_available(self) -> Optional[ComfyUIInstance]:
        """Получает свободный инстанс или ждет"""
        async with self.lock:
            for instance in self.instances:
                if not instance.busy:
                    instance.busy = True
                    return instance
        
        # Все заняты - ждем
        while True:
            await asyncio.sleep(0.1)
            async with self.lock:
                for instance in self.instances:
                    if not instance.busy:
                        instance.busy = True
                        return instance
    
    async def release(self, instance: ComfyUIInstance):
        """Освобождает инстанс"""
        async with self.lock:
            instance.busy = False
            instance.current_job = None
    
    async def health_check(self) -> dict:
        """Проверка здоровья всех инстансов"""
        results = {}
        async with aiohttp.ClientSession() as session:
            for instance in self.instances:
                try:
                    async with session.get(
                        f"{instance.url}/system_stats",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        results[instance.url] = {
                            'status': 'healthy' if resp.status == 200 else 'unhealthy',
                            'busy': instance.busy
                        }
                except:
                    results[instance.url] = {'status': 'unreachable', 'busy': instance.busy}
        return results


# Использование
pool = ComfyUIPool([
    'http://comfyui-1:8188',
    'http://comfyui-2:8189',
])

async def generate_with_pool(workflow: dict):
    instance = await pool.get_available()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{instance.url}/prompt",
                json={'prompt': workflow}
            ) as resp:
                return await resp.json()
    finally:
        await pool.release(instance)
```

---

## FAQ

### Можно ли создать параллельную генерацию на одной GPU?

**Да, но с ограничениями:**
- Каждый ComfyUI инстанс загружает модели отдельно, дублируя VRAM
- На 24GB GPU можно запустить 2 инстанции с легкими моделями (SD 1.5)
- Для SDXL/Flux — одна инстанция максимум

### Какую систему очередей выбрать?

| Ваш стек | Рекомендация |
|----------|--------------|
| Python бот | Celery + Redis |
| Node.js бот | BullMQ |
| Высокая нагрузка | RabbitMQ |
| Простой проект | Redis Streams |

### Когда переходить на Serverless?

- Непредсказуемая нагрузка (пики/простои)
- Нужен автоскейлинг
- Не хотите управлять GPU инфраструктурой
- Бюджет позволяет pay-per-use модель

### Как оптимизировать время генерации?

1. **Кэширование моделей** — держать модели в VRAM
2. **Батчинг** — группировать похожие запросы
3. **Оптимизация workflow** — убрать лишние ноды
4. **Быстрые модели** — использовать Turbo/Lightning версии

---

## Полезные ссылки

- [ComfyUI API Documentation](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI-Distributed](https://github.com/robertvoy/ComfyUI-Distributed)
- [RunPod Serverless Docs](https://docs.runpod.io/serverless/overview)
- [Celery Documentation](https://docs.celeryq.dev/)
- [BullMQ Documentation](https://bullmq.io/)

---

*Документ создан: Февраль 2026*
