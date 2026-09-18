# История изменений SkyRoutes

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [Semantic Versioning](https://semver.org/lang/ru/).

## [0.7.0] — 2026-09-18

### Добавлено
- 🌙 **Dark mode** с переключателем темы:
  - CSS-переменные для обеих тем (light/dark)
  - Кнопка переключения в шапке (☀/☾)
  - Автоопределение системной темы через `prefers-color-scheme`
  - Сохранение выбора в `localStorage`
  - Защита от FOUC (flash of unstyled content) через inline-скрипт
- 🔐 **Password reset flow** (token-based):
  - Новые модели `PasswordResetToken` и `AuditLog`
  - REST API `/api/auth/password-reset/request` и `/confirm`
  - HTML-страница `/reset` с формами
  - Токен валиден 1 час, одноразовый
  - Защита от перебора email (всегда возвращает 202)
  - Ссылка «Забыли пароль?» на странице входа
- 📝 **Audit log** для админ-действий:
  - Автоматическое логирование всех CRUD-операций с рейсами и городами
  - Запись: user_email, action, entity_type, entity_id, details, ip_address, timestamp
  - REST API `/api/admin/audit` для просмотра
  - HTML-страница `/admin/audit` с таблицей записей
- 🗜 **GZip middleware** — сжатие ответов больше 500 байт
- 📊 **Нагрузочное тестирование через locust** (`scripts/locustfile.py`):
  - 2 класса пользователей: `SkyRoutesUser` и `AnonymousBrowser`
  - 10+ сценариев: главная, поиск, города, брони, избранное
  - Headless-режим с CSV-отчётом
- 📄 **LICENSE** (MIT) и **CONTRIBUTING.md** (5 KB):
  - Правила разработки, стиль кода, именование
  - Структура коммитов (Conventional Commits)
  - Шаблон PR и баг-репорта
  - Архитектурные принципы
- 🧪 12 новых тестов в `test_auth_extended.py`:
  - Password reset: запрос, использование токена, повторное использование, невалидный
  - Audit log: пустой, с действиями, права доступа, HTML-страница, логирование CRUD

### Изменено
- Обновлён `main.py` — добавлен GZipMiddleware, роутер password_reset
- Обновлён `models.py` — добавлены модели `PasswordResetToken` и `AuditLog` с индексами
- Обновлён `crud.py` — функции `create_password_reset_token`, `verify_password_reset_token`,
  `use_password_reset_token`, `log_admin_action`, `get_audit_logs`
- Обновлён `admin.py` — все CRUD-эндпоинты теперь логируются в аудит
- Обновлён `base.html` — кнопка переключения темы, inline-скрипт для предотвращения FOUC
- Обновлён `login.html` — ссылка «Забыли пароль?»
- Обновлён `style.css` — переменные для dark/light темы, стили theme-toggle
- Обновлён `app.js` — обработчик клика по кнопке темы
- Обновлён `conftest.py` — `TRAVEL_DEBUG=True` для тестов

## [0.6.0] — 2026-09-18

### Добавлено
- 📊 **Графики на админ-панели** через Chart.js (Chart.js 4.4.1 CDN):
  - Линейный график бронирований и выручки за 14 дней
  - Doughnut-диаграмма распределения по статусам
  - Bar-чарт мин/средних/макс цен по направлениям
- 🛠 **CLI-утилита** `scripts/manage.py` с командами:
  - `create-admin`, `create-user` — создание пользователей
  - `create-flight` — создание рейсов
  - `stats` — сводная статистика в консоли
  - `reset-db` — пересоздание БД
  - `export-openapi` — экспорт OpenAPI спецификации
  - `list-routes` — список всех маршрутов API
- 📈 **Новые эндпоинты аналитики**:
  - `GET /api/admin/charts/bookings-by-day`
  - `GET /api/admin/charts/avg-prices`
  - `GET /api/admin/charts/status-breakdown`
- 📱 **PWA-манифест** для установки приложения на телефон (manifest.json)
- 🤖 **robots.txt** и **sitemap.xml** для SEO
- 📋 **API.md** — подробная документация всех REST-эндпоинтов с примерами
- 📝 **CHANGELOG.md** — этот файл
- 🔍 **CRUD-функции аналитики**: `get_bookings_by_day`, `get_avg_prices_by_route`, `get_bookings_status_breakdown`

### Изменено
- Обновлён `admin.html` — добавлены 3 графика и ссылки на новые API
- Обновлён `base.html` — добавлены manifest.json, theme-color, meta description
- Обновлён `main.py` — добавлены новые роуты для метаданных в API root

## [0.5.0] — 2026-09-17

### Добавлено
- 👤 **Страница профиля** `/profile` с личной статистикой
- ⭐ **HTML-страница избранного** `/favorites`
- 🔍 **HTML-страница истории поиска** `/search-history`
- ✅ **Подтверждение и отмена бронирования** через HTML-формы
- 🖨 **Кнопка печати / PDF** на странице просмотра брони (`window.print()`)
- 🏥 **Детальный health-check** `/api/health/detailed` с проверкой БД
- 🗄 **Docker Compose с PostgreSQL** через `--profile postgres`
- 📖 **INSTALL.md** — подробная инструкция по установке (18 KB, 13 разделов)
- 🧪 11 новых тестов в `test_new_pages.py`
- Print-friendly CSS для печати брони

### Изменено
- Обновлён `Dockerfile` — multi-stage с поддержкой `asyncpg` и `psycopg2`
- Обновлён `docker-compose.yml` — профили SQLite/PostgreSQL
- Обновлён `requirements.txt` — добавлены `asyncpg`, `psycopg2-binary`

## [0.4.0] — 2026-09-17

### Добавлено
- ⭐ **Избранные рейсы** — модель `Favorite` + REST API `/api/favorites`
- 🔍 **История поиска** — модель `SearchHistory` + API `/api/search-history`
- 🔐 **Rate limiting** через slowapi (200 запросов/мин)
- 📝 **Middleware логирования** всех HTTP-запросов с длительностью
- 📊 **In-memory метрики** на `/api/metrics`
- 🔢 **Заголовок X-Total-Count** для пагинации на клиенте
- 🗄 **Составные индексы БД** для оптимизации поиска
- 🐳 **Gunicorn config** `gunicorn_conf.py` для production
- 🔄 **GitHub Actions CI/CD** (`.github/workflows/ci.yml`) — матрица Python 3.11/3.12
- 🔧 **pre-commit хуки** (ruff + black)
- 📋 **ruff + black** конфигурация в `pyproject.toml`
- 🧪 12 новых тестов (favorites, metrics)

### Изменено
- Добавлены модели `Favorite` и `SearchHistory` в `models.py`
- Обновлён `flights.py` — сохранение истории поиска при фильтрах
- Обновлён `main.py` — middleware, rate limiter, обработчики ошибок

## [0.3.0] — 2026-09-17

### Добавлено
- 🛠 **Админ-панель** HTML `/admin` с дашбордом
- 📊 **REST API `/api/admin/flights`** — CRUD рейсов
- 📍 **REST API `/api/admin/cities`** — создание городов
- 📈 **REST API `/api/admin/stats`** и `/stats/extended`
- 🔎 **Сортировка** рейсов (`sort_by`, `sort_order`)
- 🔢 **Пагинация** через `limit`/`offset`
- 📄 **Страницы `/about` и `/contacts`** с FAQ
- 🚫 **Кастомные страницы 404 и 500** (HTML/JSON)
- 🔔 **Тосты** (уведомления) через JavaScript
- 🛠 **Makefile** с типовыми командами
- 🗄 **Alembic** для миграций БД
- 🧪 20 новых тестов (admin, pagination, pages)

## [0.2.0] — 2026-09-17

### Добавлено
- 👤 **JWT-аутентификация** (PyJWT + bcrypt)
- 📋 Страница «Мои бронирования» по email
- 🔐 Зависимости FastAPI: `get_current_user`, `require_user`, `require_admin`
- 🛠 Демо-пользователь: `demo@skyroutes.local` / `demo1234` (админ)
- 🧪 16 тестов (auth, bookings, flights)

### Изменено
- Модель `Booking` — добавлен `user_id` (FK на users)
- Конфигурация — `AliasChoices` для поддержки `TRAVEL_` префикса

## [0.1.0] — 2026-09-17

### Добавлено
- 🚀 Базовая структура FastAPI приложения
- 📋 Поиск рейсов с фильтрами (город, дата, цена, авиакомпания)
- ✈️ Бронирование нескольких пассажиров (до 9)
- 🎫 Классы обслуживания: эконом/премиум/бизнес/первый (×1.0/×1.4/×2.5/×4.0)
- 🔢 Уникальный PNR-код (6 символов)
- 🌐 REST API: cities, flights, bookings
- 🎨 Современный адаптивный UI (Inter font, CSS Grid)
- 🐳 Dockerfile + docker-compose.yml
- 🌱 Seed-скрипт: 12 городов, 140 рейсов
- 🧪 Базовые тесты (3 в `test_meta.py`)

---

Полная история коммитов: `git log --oneline` (если проект в git)
