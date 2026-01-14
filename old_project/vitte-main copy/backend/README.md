# Vitte Backend

Каркас бэкенда на FastAPI + aiogram. Включены базовые таблицы (users, dialogs, messages), healthcheck и вебхук для Telegram.

## Запуск (dev)

1. Создать виртуальное окружение и активировать его.
2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Скопировать `.env.example` в `.env` и заполнить ключи (Telegram, ProxyAPI/OpenRouter для LLM и т.д.).
4. Запустить сервер:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

По умолчанию поднимается сервис с `GET /health` и корневым `GET /`.
