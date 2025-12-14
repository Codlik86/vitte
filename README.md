# Vitte

Vitte — романтический AI-компаньон. Репозиторий оформлен как монорепо:

- `backend/` — FastAPI + aiogram, интеграции и API.
- `miniapp/` — Vite + React + TypeScript + Tailwind для UI мини-аппа.
- ComfyUI: модели/чекпоинты/LoRA лежат на GPU-хосте, а workflow-шаблон хранится в репо (`backend/app/assets/comfyui/workflows/sdxl_lora.json`) и отправляется в ComfyUI по API перед генерацией.

## Монетизация (этап 4)

- **Новые таблицы**: `subscriptions` и `purchases` (см. `backend/app/models.py`) описывают статусы подписок и покупок Store. События paywall/purchase логируются в `events_analytics`.
- **API**:
  - `/api/access/status` — расширен флагами `has_subscription`, `premium_until`, `paywall_variant`, а также списком продуктов Store.
  - `/api/payments/plans`, `/api/payments/subscribe`, `/api/payments/yookassa/webhook` — работа с подписками и YooKassa/Stars.
  - `/api/store/products`, `/api/store/purchase` — магазин дополнительных продуктов (Stars).
  - `/api/analytics/events` — логирование событий (`paywall_shown`, `paywall_cta_click`, `purchase_*` и т.д.).
- **Мини-апп**:
  - Экран Paywall имеет A/B-варианты и вызывает `subscribe` + аналитические события.
  - Заголовок отображает Premium-бейджи, страница «Свой герой» требует Premium.
  - Добавлен экран `/store` с покупками Deep Mode, Long Letters и пр.
