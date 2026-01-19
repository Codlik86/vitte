# WebApp API Requirements

## Все API эндпоинты для webapp

### Персонажи
| Метод | Endpoint | Параметры | Описание |
|-------|----------|-----------|----------|
| GET | `/api/personas` | telegram_id | Список персонажей |
| GET | `/api/personas/{id}` | telegram_id | Детали персонажа |
| POST | `/api/personas/{id}/select` | telegram_id | Выбрать персонажа |
| POST | `/api/personas/select_and_greet` | persona_id, storyId, extraDescription, settingsChanged, telegram_id | Выбрать и отправить приветствие |
| POST | `/api/personas/custom` | name, short_description, vibe, replace_existing, telegram_id | Создать кастомного персонажа |

### Доступ
| Метод | Endpoint | Параметры | Описание |
|-------|----------|-----------|----------|
| GET | `/api/access/status` | telegram_id | Статус доступа пользователя |

### Магазин
| Метод | Endpoint | Параметры | Описание |
|-------|----------|-----------|----------|
| GET | `/api/store/config` | — | Конфиг магазина (планы, пакеты, фичи) |
| GET | `/api/store/status` | telegram_id | Статус покупок пользователя |
| POST | `/api/store/buy/subscription/{code}` | telegram_id | Купить подписку |
| POST | `/api/store/buy/image_pack/{code}` | telegram_id | Купить пакет изображений |
| POST | `/api/store/buy/feature/{code}` | telegram_id | Разблокировать улучшение |

### Функции/Улучшения
| Метод | Endpoint | Параметры | Описание |
|-------|----------|-----------|----------|
| GET | `/api/features/status` | telegram_id | Статус улучшений |
| POST | `/api/features/toggle` | telegram_id, feature_code, enabled | Переключить улучшение |
| POST | `/api/features/clear-dialogs` | telegram_id | Очистить память диалогов |
| POST | `/api/features/clear-long-memory` | telegram_id | Очистить долгую память |
| POST | `/api/features/delete-account` | telegram_id | Удалить аккаунт |

### Дополнительные
| Метод | Endpoint | Параметры | Описание |
|-------|----------|-----------|----------|
| POST | `/api/chat` | telegram_id, message, mode, atmosphere, story_id, persona_id | Отправить сообщение |
| POST | `/api/bot/pay_from_miniapp` | telegram_id | Инициировать оплату через бота |
| POST | `/api/events/miniapp_open` | start_param | Логировать открытие MiniApp |
| POST | `/api/analytics/events` | telegram_id, event_type, payload | Отправить событие аналитики |

---

## Страницы webapp и их зависимости

### 1. CharactersList (Главная - список персонажей)
- **API:** `GET /api/personas`
- **Действия:** Переход к персонажу, магазину, настройкам, paywall

### 2. CharacterDetails (Детали персонажа)
- **API:** `GET /api/personas/{id}`, `POST /api/personas/select_and_greet`
- **Действия:** Выбор истории, начать разговор

### 3. CharacterCustom (Создание своего персонажа)
- **API:** `GET /api/personas`, `POST /api/personas/custom`, `POST /api/personas/select_and_greet`
- **Действия:** Создать/редактировать персонажа

### 4. Store (Магазин)
- **API:** `GET /api/store/config`, `GET /api/store/status`, `POST /api/store/buy/*`
- **Действия:** Покупка пакетов изображений и улучшений

### 5. Paywall (Подписка)
- **API:** `GET /api/store/config`, `GET /api/store/status`, `POST /api/store/buy/subscription/{code}`
- **Действия:** Покупка подписки

### 6. Settings (Настройки)
- **API:** `GET /api/features/status`, `POST /api/features/toggle`, `POST /api/features/clear-*`, `POST /api/features/delete-account`
- **Действия:** Управление улучшениями, очистка памяти, удаление аккаунта

---

## Приоритет реализации

### Критичные (без них webapp не работает)
1. `GET /api/personas` - главная страница
2. `GET /api/personas/{id}` - детали персонажа
3. `GET /api/access/status` - используется везде для проверки доступа
4. `GET /api/store/config` - магазин и paywall
5. `GET /api/store/status` - статус покупок

### Важные (функционал)
6. `POST /api/personas/select_and_greet` - начать разговор
7. `POST /api/personas/custom` - создание персонажа
8. `GET /api/features/status` - настройки
9. `POST /api/features/toggle` - переключение улучшений

### Вторичные
10. Покупки в магазине (`POST /api/store/buy/*`)
11. Очистка памяти и удаление аккаунта
12. Аналитика и события
