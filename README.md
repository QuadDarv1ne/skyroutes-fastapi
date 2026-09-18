# SkyRoutes — заготовка сайта путешествий и авиаперелётов на FastAPI

Production-ready сервис поиска и бронирования авиабилетов с JWT-аутентификацией,
профилем пользователя, избранными рейсами, историей поиска, админ-панелью с графиками,
audit log, dark mode, REST API, HTML-интерфейсом, тестами, CI/CD и Docker.

📚 **Документация:**
- 📖 [INSTALL.md](INSTALL.md) — подробная инструкция по установке и запуску (14 разделов)
- 🔌 [API.md](API.md) — документация всех REST-эндпоинтов с примерами
- 📝 [CHANGELOG.md](CHANGELOG.md) — история изменений по версиям
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) — правила для контрибьюторов
- ⚖ [LICENSE](LICENSE) — MIT лицензия

**Технологии:** FastAPI 0.115 · SQLAlchemy 2.0 (async) · Pydantic v2 · Jinja2 ·
JWT (PyJWT) + bcrypt · slowapi (rate limiting) · SQLite/PostgreSQL · Alembic ·
Gunicorn · Docker · Chart.js · locust · pytest · ruff + black · GitHub Actions

## Возможности

### 👤 Пользователи
- Регистрация и вход по JWT (Bearer для API, httponly-cookie для HTML)
- 🔐 **Password reset flow** — восстановление пароля через одноразовый токен (1 час)
- **Страница профиля** с личной статистикой (потрачено, активные брони, избранное)
- Хеширование паролей через bcrypt
- Страница «Мои бронирования» — для залогиненных и по email
- Подтверждение и отмена бронирования (с возвратом мест в рейс)

### 🔎 Рейсы и поиск
- Поиск с фильтрами: город, диапазон дат, максимальная цена, авиакомпания
- **Сортировка** по времени вылета, цене или длительности (asc/desc)
- **Пагинация** через `limit`/`offset` + заголовок `X-Total-Count`
- **История поиска** — сохраняется автоматически для залогиненных + HTML-страница
- 12 тестовых городов и 140 рейсов на 7 дней
- Гибкая цена по классу обслуживания (×1.0 / ×1.4 / ×2.5 / ×4.0)
- Составные индексы БД для быстрого поиска по маршруту и дате

### ⭐ Избранные рейсы
- Добавление/удаление через HTML-форму (♥ на странице поиска)
- Отдельная HTML-страница `/favorites` со списком избранных рейсов
- REST API `/api/favorites` — GET/POST/DELETE с авторизацией
- Защита от дубликатов через `UniqueConstraint`

### 📋 Бронирование
- Много пассажиров в одной брони (до 9)
- Уникальный PNR-код (6 символов без неоднозначных)
- Статусы: `pending` → `confirmed` / `cancelled`
- Подтверждение/отмена через HTML-форму на странице брони
- **Кнопка печати / сохранения в PDF** через `window.print()`
- Контроль доступных мест с автоматическим возвратом при отмене

### 🛠 Админ-панель
- HTML-страница `/admin` с дашбордом: счётчики, выручка, популярные направления, топ авиакомпаний
- 📊 **Графики через Chart.js**:
  - Линейный график бронирований и выручки за 14 дней
  - Doughnut-диаграмма распределения по статусам
  - Bar-чарт мин/средних/макс цен по направлениям
- REST API `/api/admin/flights` — CRUD рейсов
- REST API `/api/admin/cities` — создание новых городов
- REST API `/api/admin/stats` и `/api/admin/stats/extended`
- 📈 REST API для графиков:
  - `/api/admin/charts/bookings-by-day`
  - `/api/admin/charts/avg-prices`
  - `/api/admin/charts/status-breakdown`
- 📝 **Audit log** — автоматическое логирование всех админ-действий:
  - REST API `/api/admin/audit` — список последних записей
  - HTML-страница `/admin/audit` с таблицей
  - Записывает: user, action, entity, IP, timestamp
- Все админ-эндпоинты требуют JWT с `is_admin=True`

### 🔐 Безопасность и производительность
- **Rate limiting** через slowapi (200 запросов/мин)
- **Middleware логирования** всех запросов с длительностью
- **GZip сжатие** ответов больше 500 байт
- **In-memory метрики** на `/api/metrics`
- **Детальный health-check** на `/api/health/detailed` с проверкой БД
- Кастомные обработчики 404 и 500 (HTML для браузера, JSON для API)
- Структурированное логирование
- 🔐 **Password reset flow** с одноразовыми токенами (защита от перебора email)
- 📝 **Audit log** всех админ-действий

### 🌐 REST API
- `/api/auth/*` — JWT-аутентификация + password reset
- `/api/cities` — справочник городов
- `/api/flights` — поиск с сортировкой, пагинацией, X-Total-Count
- `/api/bookings` — CRUD бронирований
- `/api/favorites` — **избранные рейсы**
- `/api/search-history` — **история поиска**
- `/api/admin/*` — админ-эндпоинты
- `/api/health` и `/api/health/detailed` — health-check
- `/api/metrics` — счётчики запросов
- `/docs` — автоматическая Swagger-документация

### 🎨 UI
- Современный адаптивный дизайн (Inter font, CSS Grid)
- 🌙 **Dark mode** с переключателем (☀/☾), автоопределение системной темы
- Главная, поиск рейсов с сортировкой, форма бронирования, подтверждение с печатью
- Страницы входа/регистрации/профиля/избранного/истории/мои брони
- Страницы `/about` и `/contacts` с FAQ
- Кастомные страницы 404 и 500 (HTML для браузера, JSON для API)
- Тосты (уведомления) через JavaScript
- SVG-фавикон (✈)
- Print-friendly CSS для печати брони

### 🛠 DevOps
- Dockerfile + docker-compose.yml (с профилями для SQLite и PostgreSQL)
- Gunicorn config для production
- **CLI-утилита** `scripts/manage.py` для управления (create-admin, stats, reset-db, export-openapi, list-routes)
- Alembic для миграций БД
- Makefile с типовыми командами
- GitHub Actions CI/CD на Python 3.11/3.12
- pre-commit хуки (ruff + black)
- pytest + httpx + pytest-asyncio (**78 тестов, все проходят**)
- 📊 **Нагрузочное тестирование** через locust (`scripts/locustfile.py`)
- 📱 **PWA-манифест** для установки на телефон
- 🤖 **robots.txt** и **sitemap.xml** для SEO
- 📄 **LICENSE (MIT)** и **CONTRIBUTING.md** для open-source готовности

## Структура проекта

```
my-project/
├── app/
│   ├── main.py           # FastAPI: middleware, rate limiter, обработчики ошибок
│   ├── config.py         # Pydantic Settings с AliasChoices
│   ├── database.py       # Async engine, сессии
│   ├── models.py         # ORM: City, Flight, User, Passenger, Booking, Favorite, SearchHistory
│   ├── schemas.py        # Pydantic-схемы + FlightCreate, StatsResponse
│   ├── crud.py           # CRUD: поиск, бронирования, статистика, favorites, history
│   ├── security.py       # JWT, bcrypt, зависимости FastAPI
│   ├── seed.py           # Тестовые данные + демо-пользователь
│   ├── routers/
│   │   ├── auth.py       # /api/auth/* (register, login, me)
│   │   ├── cities.py     # /api/cities
│   │   ├── flights.py    # /api/flights (+ X-Total-Count, search history)
│   │   ├── bookings.py   # /api/bookings
│   │   ├── favorites.py  # /api/favorites
│   │   ├── search_history.py # /api/search-history
│   │   ├── admin.py      # /api/admin/*
│   │   └── pages.py      # HTML: profile, favorites, search-history, confirm/cancel
│   ├── templates/        # base, index, flights, booking, login, register,
│   │                     # profile, favorites, search_history, my_bookings,
│   │                     # admin, about, contacts, 404, error
│   └── static/           # CSS (с print-friendly), JS (тосты, сортировка)
├── tests/                # 78 pytest-тестов
│   ├── conftest.py
│   ├── test_meta.py      # health, root, cities (3)
│   ├── test_auth.py      # регистрация, логин, /me (6)
│   ├── test_auth_extended.py # password reset, audit log (12, новый!)
│   ├── test_flights.py   # города, рейсы, фильтры (3)
│   ├── test_bookings.py  # создание, просмотр, отмена (4)
│   ├── test_admin.py     # admin CRUD и статистика (9)
│   ├── test_pagination.py # пагинация и сортировка (5)
│   ├── test_pages.py     # about, contacts, 404 (6)
│   ├── test_favorites.py # избранное (6)
│   ├── test_metrics.py   # метрики и история (6)
│   ├── test_new_pages.py # profile, favorites HTML, confirm/cancel (11)
│   └── test_charts.py    # графики аналитики (7)
├── alembic/              # Миграции БД
├── .github/workflows/
│   └── ci.yml            # GitHub Actions CI
├── scripts/
│   ├── test_api.py       # Интеграционный smoke-тест
│   ├── manage.py         # CLI-утилита
│   └── locustfile.py     # Нагрузочное тестирование (новый!)
├── INSTALL.md            # Подробная инструкция по установке (14 разделов)
├── API.md                # Документация REST API
├── CHANGELOG.md          # История изменений
├── CONTRIBUTING.md       # Правила для контрибьюторов (новый!)
├── LICENSE               # MIT лицензия (новый!)
├── README.md
├── requirements.txt
├── Dockerfile            # Multi-stage с поддержкой PostgreSQL
├── docker-compose.yml    # Профили: default (SQLite), postgres (PostgreSQL)
├── gunicorn_conf.py      # Production config
├── Makefile
├── pyproject.toml        # ruff + black конфиг
├── .black.toml
├── .pre-commit-config.yaml
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── pytest.ini
└── run.py
```

## Быстрый старт

### Самый простой способ (Makefile)

```bash
make venv install seed run
```

Откройте http://localhost:8000

### Через Docker (SQLite)

```bash
docker compose up --build
```

### Через Docker (PostgreSQL)

```bash
docker compose --profile postgres up --build
```

### Production через Gunicorn

```bash
pip install -r requirements.txt
python -m app.seed
gunicorn app.main:app -c gunicorn_conf.py
```

📖 **Все способы запуска подробно описаны в [INSTALL.md](INSTALL.md)**

## CLI-утилита manage.py

Управление проектом через командную строку:

```bash
# Создать администратора
python scripts/manage.py create-admin --email admin@x.com --password secret --name "Admin"

# Создать обычного пользователя
python scripts/manage.py create-user --email user@x.com --password secret --name "User"

# Создать рейс
python scripts/manage.py create-flight \
  --number SU9999 --airline "Аэрофлот" --origin 1 --dest 3 \
  --dep "2026-10-01T10:00" --arr "2026-10-01T13:00" --price 25000 --seats 200

# Сводная статистика в консоли
python scripts/manage.py stats

# Сбросить БД (с подтверждением)
python scripts/manage.py reset-db

# Экспорт OpenAPI спецификации в JSON
python scripts/manage.py export-openapi --output openapi.json

# Список всех маршрутов API
python scripts/manage.py list-routes
```

## Демо-аккаунт

После `python -m app.seed`:

| Email | Пароль | Роль |
|---|---|---|
| `demo@skyroutes.local` | `demo1234` | администратор |

## Тесты

```bash
# 78 pytest-тестов (~15 секунд)
pytest tests/ -v

# Интеграционный smoke-тест (поднимает uvicorn и проходит все сценарии)
python scripts/test_api.py

# Нагрузочное тестирование через locust
pip install locust
locust -f scripts/locustfile.py --headless --host http://localhost:8000 \
    --users 50 --spawn-rate 5 --run-time 60s

# Через Makefile
make test
make test-api
```

```
$ pytest tests/ -v
============================== 78 passed in 19.76s ==============================
```

Покрытие тестами:
- `test_meta.py` — health, root API, cities (3)
- `test_auth.py` — регистрация, дубликаты, логин, /me (6)
- `test_auth_extended.py` — password reset, audit log (12, новый!)
- `test_flights.py` — города, рейсы, фильтры (3)
- `test_bookings.py` — создание, просмотр, отмена (4)
- `test_admin.py` — CRUD рейсов, города, статистика (9)
- `test_pagination.py` — пагинация, сортировка (5)
- `test_pages.py` — about, contacts, 404 HTML/JSON (6)
- `test_favorites.py` — избранное (6)
- `test_metrics.py` — метрики, история, X-Total-Count (6)
- `test_new_pages.py` — profile, favorites HTML, confirm/cancel, health/detailed (11)
- `test_charts.py` — графики аналитики: avg-prices, status-breakdown (7)

## Makefile команды

```bash
make help        # список всех команд
make venv        # создать виртуальное окружение
make install     # установить зависимости
make seed        # заполнить БД тестовыми данными
make run         # запустить production-сервер
make dev         # запустить dev-сервер (с reload)
make test        # запустить pytest
make test-api    # запустить интеграционный smoke-тест
make clean       # удалить временные файлы
make docker-up   # запустить через docker compose
make docker-down # остановить docker compose
```

## API эндпоинты

| Метод | URL | Описание |
|---|---|---|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Вход (OAuth2PasswordRequestForm) |
| GET | `/api/auth/me` | Текущий пользователь |
| POST | `/api/auth/password-reset/request` | Запросить сброс пароля (новое!) |
| POST | `/api/auth/password-reset/confirm` | Установить новый пароль (новое!) |
| GET | `/api/cities` | Список городов |
| GET | `/api/flights` | Поиск рейсов (сортировка, пагинация) |
| GET | `/api/flights/{id}` | Детали рейса |
| POST | `/api/bookings` | Создать бронирование |
| GET | `/api/bookings/{code}` | Найти бронь по PNR |
| PATCH | `/api/bookings/{code}` | Изменить статус |
| GET | `/api/bookings` | Мои бронирования (нужен токен) |
| GET | `/api/favorites` | Избранные рейсы |
| POST | `/api/favorites/{flight_id}` | Добавить в избранное |
| DELETE | `/api/favorites/{flight_id}` | Удалить из избранного |
| GET | `/api/search-history` | История поиска |
| POST | `/api/admin/flights` | Создать рейс (admin) |
| PATCH | `/api/admin/flights/{id}` | Обновить рейс (admin) |
| DELETE | `/api/admin/flights/{id}` | Деактивировать рейс (admin) |
| POST | `/api/admin/cities` | Создать город (admin) |
| GET | `/api/admin/stats` | Сводная статистика (admin) |
| GET | `/api/admin/stats/extended` | С топами (admin) |
| GET | `/api/admin/charts/bookings-by-day` | Данные графика (admin) |
| GET | `/api/admin/charts/avg-prices` | Средние цены (admin) |
| GET | `/api/admin/charts/status-breakdown` | По статусам (admin) |
| GET | `/api/admin/audit` | Аудит-лог действий (admin, новое!) |
| GET | `/api/health` | Health-check |
| GET | `/api/health/detailed` | С зависимостями (БД) |
| GET | `/api/metrics` | Метрики запросов |

📖 **Подробное описание всех эндпоинтов с примерами — [API.md](API.md)**

## HTML-страницы

| URL | Описание |
|---|---|
| `/` | Главная |
| `/flights` | Поиск рейсов с сортировкой |
| `/booking/{flight_id}` | Форма бронирования |
| `/booking/{code}/view` | Просмотр брони + кнопка печати |
| `/login`, `/register`, `/logout` | Авторизация |
| `/reset` | Сброс пароля (новое!) |
| `/profile` | Профиль пользователя со статистикой |
| `/favorites` | Избранные рейсы |
| `/my-bookings` | Мои бронирования |
| `/search-history` | История поиска |
| `/admin` | Админ-панель с графиками (для админа) |
| `/admin/audit` | Аудит-лог действий (новое!) |
| `/about` | О проекте |
| `/docs` | Swagger UI |

## Что можно докрутить дальше

- 🔐 OAuth2 через Google/GitHub
- 💳 Платёжный шлюз (ЮKassa, Stripe)
- 📧 Email-уведомления (FastAPI-Mail + Celery)
- 🌍 Интеграция с реальными GDS (Amadeus, Sabre) или Skyscanner API
- 🔍 Полнотекстовый поиск (Elasticsearch / Meilisearch)
- 📈 Графики на странице статистики (Chart.js / ECharts)
- 🚀 Redis для кэширования и rate limiting
- 📱 PWA-манифест
- 📊 OpenTelemetry для распределённой трассировки
- 🔔 WebSocket для real-time обновления цен

## Лицензия

MIT — используй свободно.
