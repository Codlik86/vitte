# Vitte

Vitte — романтический AI-компаньон. Репозиторий оформлен как монорепо:

- `backend/` — FastAPI + aiogram, интеграции и API.
- `miniapp/` — Vite + React + TypeScript + Tailwind для UI мини-аппа.

## Быстрый старт (черновик)

### Backend
1. Создать и активировать venv.
2. Установить зависимости: `pip install -r backend/requirements.txt`.
3. Запустить сервер: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (из папки `backend`).

### Miniapp
1. Перейти в `miniapp` и установить зависимости: `npm install`.
2. Запустить dev-сервер: `npm run dev`.

Подробнее см. README в соответствующих папках.
