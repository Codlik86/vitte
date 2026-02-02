# Grafana Admin Panel - Setup Guide

Полноценная админка на базе Grafana для управления Vitte Bot.

## 🔍 Поиск по Telegram ID

**Все дашборды имеют поле поиска по Telegram ID!**

Просто введите Telegram ID в поле вверху любого дашборда, и вы получите:
- Фильтрацию данных по этому пользователю
- Ссылку на **Карточку юзера** с полной информацией
- Контекстные данные (платежи, активность и т.д.)

---

## 📊 Дашборды

### 1. Управление пользователями
**URL:** `/d/users-management`

Таблица всех пользователей с колонками:
- Telegram ID (кликабельная ссылка на карточку юзера)
- **UTM метка** (откуда пришел пользователь)
- Имя, Фамилия, Username
- Язык
- Дата регистрации
- Количество платежей
- Потрачено звезд ⭐
- Наличие подписки
- План подписки
- Есть ли улучшения

**Поиск:**
- По Telegram ID (поле вверху)
- По UTM метке (фильтр)
- По имени/username (текстовый поиск)

---

### 2. Платежи и доходы
**URL:** `/d/payments-revenue`

#### Блоки с цифрами:
- 💰 Доход сегодня (stars)
- 💰 Доход за месяц (stars)
- 💰 Доход за все время (stars)

#### Таблицы:
1. **Последние платежи** - все транзакции с фильтром по User ID
2. **Топ платящих пользователей** (топ 50)

**Поиск:** По Telegram ID

---

### 3. Технические метрики
**URL:** `/d/technical-metrics`

**Поиск:** По Telegram ID (поле вверху) → переход на карточку юзера

#### Счетчики:
- Всего пользователей
- Активных за 24ч
- Всего диалогов
- Активных диалогов
- Всего сообщений
- Среднее сообщений/юзер
- Активных подписок

#### Графики:
- Регистрации (последние 7 дней)
- Сообщения (последние 7 дней)

---

### 4. Карточка юзера
**URL:** `/d/user-card?var-telegram_id=<ID>`

Полная информация о пользователе:

#### Основная информация:
- Telegram ID
- Username
- Имя, Фамилия
- Дата регистрации
- Последняя активность

#### Платежи и подписка:
- Потрачено звезд
- Количество платежей
- Наличие подписки
- План подписки

#### Активность:
- Всего сообщений
- Активных диалогов

#### Улучшения:
- Список разблокированных фич
- Куплено изображений
- Остаток изображений

**Доступ:** Через поле "Telegram ID" вверху или клик по ID в других дашбордах

---

### 5. Сервис рассылки
**URL:** `/d/broadcast-service`

**Поиск:** По Telegram ID (поле вверху) → переход на карточку юзера

Статус: В разработке (пока пустой дашборд)

---

## 🎯 UTM Tracking

### Как работает UTM отслеживание

Когда пользователь переходит по ссылке с UTM меткой, она **автоматически сохраняется** при первой регистрации:

#### Формат ссылки:
```
https://t.me/vitteaidevbot?start=<utm_source>
```

#### Примеры:
```bash
# Рекламная кампания Facebook
https://t.me/vitteaidevbot?start=fb_ads_winter2026

# Инфлюенсер
https://t.me/vitteaidevbot?start=influencer_ivanov

# YouTube реклама
https://t.me/vitteaidevbot?start=youtube_promo_jan

# Email рассылка
https://t.me/vitteaidevbot?start=email_newsletter_01

# Партнерская программа
https://t.me/vitteaidevbot?start=partner_tech_blog
```

#### Что происходит:
1. Пользователь кликает по ссылке → открывается бот
2. Telegram отправляет команду `/start <utm_source>`
3. Бот извлекает UTM метку из команды
4. При создании пользователя UTM **сохраняется в поле `utm_source`**
5. UTM **навсегда привязана** к пользователю (не меняется)

#### Где посмотреть UTM:
- **Управление пользователями** - колонка "UTM метка"
- **Карточка юзера** - блок "Основная информация"
- **API endpoint** - `/analytics/users/all?utm_source=fb_ads_winter2026`

#### Логирование:
```bash
# Проверить что UTM отбивается в логах
docker logs vitte_bot | grep "UTM"

# Пример:
# INFO - UTM source detected: fb_ads_winter2026 for user 123456789
# INFO - New user registered: 123456789 (@username) with 10 free images | UTM: fb_ads_winter2026
```

---

## 🚀 Запуск

### Шаг 1: Применить миграцию UTM

```bash
cd telegram-bot-microservices

# Применить миграцию
docker exec -it vitte_postgres psql -U vitte_user -d vitte_bot -c "
ALTER TABLE users ADD COLUMN IF NOT EXISTS utm_source VARCHAR(255);
CREATE INDEX IF NOT EXISTS ix_users_utm_source ON users(utm_source);
"
```

### Шаг 2: Перезапустить сервисы

```bash
# Остановить Grafana и Admin
docker compose stop grafana admin

# Пересобрать Admin (новые API endpoints)
docker compose up -d --build admin

# Запустить Grafana с provisioning
docker compose up -d grafana

# Проверить статус
docker compose ps grafana admin
```

### Шаг 3: Проверить установку Infinity plugin

```bash
# Проверить логи Grafana
docker logs vitte_grafana | grep -i infinity

# Должно быть:
# "Successfully installed plugin: yesoreyeram-infinity-datasource"
```

### Шаг 4: Доступ к Grafana

#### Вариант 1: Локальный доступ (через SSH tunnel)

```bash
# На локальной машине
ssh -L 3000:localhost:3000 ubuntu@vittecpu

# Открыть в браузере:
http://localhost:3000

# Логин: admin
# Пароль: из переменной $GRAFANA_PASSWORD
```

#### Вариант 2: Через Nginx (production)

Добавить в `nginx.conf`:

```nginx
# Grafana Admin Panel (internal)
server {
    listen 80;
    server_name grafana.vitte.local;

    location / {
        proxy_pass http://grafana:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support для live updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Затем перезапустить Nginx:
```bash
docker compose restart nginx
```

Добавить DNS запись или в `/etc/hosts`:
```
<SERVER_IP> grafana.vitte.local
```

---

## 📡 API Endpoints

Все эндпоинты доступны через Admin service (порт 8080):

### Users Management
- `GET /analytics/users/all?skip=0&limit=100&telegram_id=<id>&utm_source=<utm>&search=<query>`
- Возвращает список пользователей с полной информацией

### Revenue
- `GET /analytics/revenue/summary`
- Возвращает доход (сегодня, месяц, все время)

### Payments
- `GET /analytics/payments/recent?skip=0&limit=100&telegram_id=<id>`
- Последние платежи

- `GET /analytics/payments/top-spenders?limit=50`
- Топ платящих пользователей

### User Card
- `GET /analytics/user/<telegram_id>/card`
- Полная карточка пользователя

### Technical Stats
- `GET /analytics/tech/stats`
- Технические метрики системы

### Broadcast (placeholder)
- `GET /analytics/broadcast/stats`
- Статистика рассылок (пока заглушка)

---

## 🔧 Конфигурация

### Datasources

**PostgreSQL** (default):
- Host: `postgres:5432`
- Database: `${POSTGRES_DB}`
- User: `${POSTGRES_USER}`
- Используется для графиков временных рядов

**Admin API** (Infinity plugin):
- URL: `http://admin:8080`
- Используется для таблиц и счетчиков

**Prometheus**:
- URL: `http://prometheus:9090`
- Для будущих метрик производительности

---

## 🛠️ Troubleshooting

### Grafana не запускается

```bash
# Проверить логи
docker logs vitte_grafana --tail 100

# Проверить provisioning файлы
docker exec vitte_grafana ls -la /etc/grafana/provisioning/datasources
docker exec vitte_grafana ls -la /etc/grafana/dashboards
```

### Infinity plugin не установился

```bash
# Переустановить вручную
docker exec -it vitte_grafana grafana-cli plugins install yesoreyeram-infinity-datasource

# Перезапустить
docker compose restart grafana
```

### Datasource не подключается

```bash
# Проверить доступность Admin API
docker exec vitte_grafana curl -v http://admin:8080/analytics/tech/stats

# Проверить доступность PostgreSQL
docker exec vitte_grafana pg_isready -h postgres -p 5432 -U vitte_user
```

### Дашборды не загружаются

```bash
# Проверить что файлы смонтированы
docker exec vitte_grafana ls -la /etc/grafana/dashboards/

# Проверить JSON на валидность
cat infrastructure/monitoring/grafana/dashboards/users_management.json | jq .
```

### API возвращает ошибки

```bash
# Проверить логи Admin service
docker logs vitte_admin --tail 100

# Проверить что миграция применена
docker exec -it vitte_postgres psql -U vitte_user -d vitte_bot -c "\\d users"
# Должна быть колонка utm_source
```

---

## 📝 Изменения в проекте

### Файлы созданы:
```
telegram-bot-microservices/
├── alembic/versions/
│   └── 20260126_add_utm_source.py                    # Миграция UTM
├── services/bot/admin/app/routes/
│   └── analytics.py                                   # API endpoints для админки (600+ строк)
├── infrastructure/monitoring/grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yml                       # PostgreSQL + Admin API + Prometheus
│   │   └── dashboards/
│   │       └── dashboards.yml                         # Provisioning config
│   └── dashboards/
│       ├── users_management.json                      # Управление пользователями
│       ├── payments_revenue.json                      # Платежи и доходы
│       ├── technical_metrics.json                     # Технические метрики (с поиском)
│       ├── user_card.json                             # Карточка юзера
│       └── broadcast_service.json                     # Сервис рассылки (с поиском)
└── GRAFANA_ADMIN_SETUP.md                            # Эта инструкция
```

### Файлы изменены:
- `shared/database/models.py` - добавлено поле `utm_source` в User
- `shared/database/services.py` - параметр `utm_source` в create_user()
- `services/bot/app/handlers/start.py` - **захват UTM метки из /start команды**
- `services/bot/admin/app/main.py` - добавлен analytics_router
- `docker-compose.yml` - обновлен Grafana с provisioning + Infinity plugin

---

## 🎯 Следующие шаги

1. **Добавить Nginx роут для Grafana** (если нужен публичный доступ)
2. **Настроить оповещения** (Alerts в Grafana)
3. **Добавить дашборд Redis метрик** (memory, hit rate, keys)
4. **Реализовать сервис рассылки** и заполнить дашборд
5. **Добавить дашборд LLM метрик** (токены, latency, errors)

---

## 📸 Screenshots

После запуска дашборды будут доступны по адресам:
- http://localhost:3000/dashboards (список всех дашбордов)
- http://localhost:3000/d/users-management (управление пользователями)
- http://localhost:3000/d/payments-revenue (платежи)
- http://localhost:3000/d/technical-metrics (технические метрики)
- http://localhost:3000/d/user-card (карточка юзера)
- http://localhost:3000/d/broadcast-service (рассылки)

---

**Дата создания:** 2026-01-26
**Версия:** 1.0.0
**Автор:** Claude + Adam
