# Инструкция по установке и запуску SkyRoutes

Полное руководство по развёртыванию проекта SkyRoutes на FastAPI в разных окружениях: локально, через Docker, с PostgreSQL и в production.

📚 **Дополнительная документация:**
- [README.md](README.md) — общее описание проекта
- [API.md](API.md) — подробная документация всех REST-эндпоинтов с примерами
- [CHANGELOG.md](CHANGELOG.md) — история изменений по версиям
- [CONTRIBUTING.md](CONTRIBUTING.md) — правила для контрибьюторов
- [LICENSE](LICENSE) — MIT лицензия

---

## Содержание

1. [Требования](#1-требования)
2. [Быстрый старт (локально, SQLite)](#2-быстрый-старт-локально-sqlite)
3. [Запуск через Docker (SQLite)](#3-запуск-через-docker-sqlite)
4. [Запуск через Docker (PostgreSQL)](#4-запуск-через-docker-postgresql)
5. [Локальный запуск с PostgreSQL](#5-локальный-запуск-с-postgresql)
6. [Production-запуск через Gunicorn](#6-production-запуск-через-gunicorn)
7. [Переменные окружения](#7-переменные-окружения)
8. [Заполнение БД тестовыми данными](#8-заполнение-бд-тестовыми-данными)
9. [Запуск тестов](#9-запуск-тестов)
10. [Миграции БД через Alembic](#10-миграции-бд-через-alembic)
11. [Запуск CI/CD через GitHub Actions](#11-запуск-cicd-через-github-actions)
12. [Настройка pre-commit хуков](#12-настройка-pre-commit-хуков)
13. [CLI-утилита manage.py](#13-cli-утилита-managepy)
14. [Нагрузочное тестирование (locust)](#14-нагрузочное-тестирование-locust)
15. [Dark mode](#15-dark-mode)
16. [Решение проблем (Troubleshooting)](#16-решение-проблем-troubleshooting)

---

## 1. Требования

| Компонент | Минимальная версия | Рекомендуется |
|---|---|---|
| Python | 3.11+ | 3.12 |
| pip | 23+ | 25+ |
| Docker | 24+ | 27+ |
| Docker Compose | v2+ | v2.30+ |
| PostgreSQL (опц.) | 14+ | 16 |

**Поддерживаемые ОС:** Linux (Ubuntu/Debian, Fedora, Arch), macOS, Windows (через WSL2).

---

## 2. Быстрый старт (локально, SQLite)

Самый простой способ запустить проект — через SQLite (не требует внешних БД).

### Шаг 1: Клонирование и создание venv

```bash
# Если распаковали архив — перейдите в папку
cd skyroutes

# Создаём виртуальное окружение
python -m venv .venv

# Активируем (Linux/macOS)
source .venv/bin/activate
# Или (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### Шаг 2: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 3: Конфигурация

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Минимально достаточный `.env` (для разработки):

```env
TRAVEL_DEBUG=True
TRAVEL_SECRET_KEY=любая-случайная-строка-минимум-32-символа
TRAVEL_DATABASE_URL=sqlite+aiosqlite:///./travel.db
```

Сгенерировать надёжный secret_key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Шаг 4: Заполнение БД тестовыми данными

```bash
python -m app.seed
```

Вывод:
```
✓ Добавлено городов: 12
✓ Добавлено рейсов: 140
✓ Всего городов: 12
✓ Всего рейсов: 140
✓ Создан демо-пользователь: demo@skyroutes.local / demo1234
```

### Шаг 5: Запуск приложения

**Вариант A: Dev-сервер (с авто-reload):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Вариант B: Через run.py:**
```bash
python run.py
```

**Вариант C: Через Makefile:**
```bash
make dev
```

Откройте в браузере: http://localhost:8000

---

## 3. Запуск через Docker (SQLite)

Простейший Docker-запуск без установки Python:

```bash
# Сборка и запуск
docker compose up --build

# В фоне
docker compose up -d --build

# Просмотр логов
docker compose logs -f app

# Остановка
docker compose down
```

Приложение будет доступно на http://localhost:8000

**Важно:** SQLite-файл сохраняется в Docker volume `app-data`, поэтому данные не теряются между перезапусками контейнера.

---

## 4. Запуск через Docker (PostgreSQL)

Production-конфигурация с PostgreSQL:

```bash
# Запуск с профилем postgres
docker compose --profile postgres up --build

# В фоне
docker compose --profile postgres up -d --build

# Остановка (с удалением данных)
docker compose --profile postgres down -v
```

Приложение запустится на http://localhost:8000, а PostgreSQL — на http://localhost:5432.

**Подключение к PostgreSQL:**
- Хост: `localhost`
- Порт: `5432`
- БД: `skyroutes`
- Пользователь: `skyroutes`
- Пароль: `skyroutes`

---

## 5. Локальный запуск с PostgreSQL

### Шаг 1: Установка PostgreSQL

**Linux (Ubuntu/Debian):**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

### Шаг 2: Создание БД и пользователя

```bash
sudo -u postgres psql << 'SQL'
CREATE USER skyroutes WITH PASSWORD 'skyroutes';
CREATE DATABASE skyroutes OWNER skyroutes;
GRANT ALL PRIVILEGES ON DATABASE skyroutes TO skyroutes;
SQL
```

### Шаг 3: Установка драйвера

Драйвер `asyncpg` уже включён в `requirements.txt`, но при необходимости:

```bash
pip install asyncpg
```

### Шаг 4: Настройка `.env`

```env
TRAVEL_DATABASE_URL=postgresql+asyncpg://skyroutes:skyroutes@localhost:5432/skyroutes
TRAVEL_SECRET_KEY=ваш-длинный-случайный-ключ
TRAVEL_DEBUG=True
```

### Шаг 5: Запуск

```bash
python -m app.seed      # заполнить БД
python run.py           # запустить приложение
```

---

## 6. Production-запуск через Gunicorn

Для production используйте Gunicorn с uvicorn worker'ами:

### Локально

```bash
pip install -r requirements.txt
python -m app.seed

# Запуск (workers = 2 × CPU + 1)
gunicorn app.main:app -c gunicorn_conf.py

# С переопределением параметров
BIND=0.0.0.0:8080 WORKERS=8 gunicorn app.main:app -c gunicorn_conf.py
```

### В Docker

Dockerfile по умолчанию использует Gunicorn:

```bash
docker compose up --build
```

### Конфигурация Gunicorn (`gunicorn_conf.py`)

| Параметр | По умолчанию | Описание |
|---|---|---|
| `BIND` | `0.0.0.0:8000` | Адрес привязки |
| `WORKERS` | `(CPU × 2) + 1` | Кол-во worker-процессов |
| `TIMEOUT` | `120` | Таймаут воркера (сек) |
| `GRACEFUL_TIMEOUT` | `30` | Плавная остановка |
| `KEEPALIVE` | `5` | Keep-alive соединения |
| `LOG_LEVEL` | `info` | Уровень логирования |
| `MAX_REQUESTS` | `1000` | Перезапуск worker'а после N запросов |
| `RELOAD` | `false` | Авто-reload (только для dev) |

---

## 7. Переменные окружения

Все переменные читаются с префиксом `TRAVEL_` или без него (с `TRAVEL_` — приоритет):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TRAVEL_APP_NAME` | `SkyRoutes — Путешествия и Авиаперелёты` | Название приложения |
| `TRAVEL_APP_VERSION` | `0.5.0` | Версия |
| `TRAVEL_DEBUG` | `True` | Режим отладки |
| `TRAVEL_DATABASE_URL` | `sqlite+aiosqlite:///./travel.db` | URL БД |
| `TRAVEL_CURRENCY` | `RUB` | Код валюты |
| `TRAVEL_CURRENCY_SYMBOL` | `₽` | Символ валюты |
| `TRAVEL_PAGE_SIZE` | `10` | Кол-во результатов на странице |
| `TRAVEL_SECRET_KEY` | `change-me...` | **Секретный ключ JWT — поменяй в проде!** |
| `TRAVEL_JWT_ALGORITHM` | `HS256` | Алгоритм подписи JWT |
| `TRAVEL_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 часа) | Время жизни токена |

### Пример production `.env`

```env
TRAVEL_APP_NAME="SkyRoutes Production"
TRAVEL_DEBUG=False
TRAVEL_DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/skyroutes
TRAVEL_SECRET_KEY=__сгенерируй_через_secrets.token_urlsafe(48)__
TRAVEL_ACCESS_TOKEN_EXPIRE_MINUTES=720
TRAVEL_CURRENCY=RUB
TRAVEL_CURRENCY_SYMBOL=₽
TRAVEL_PAGE_SIZE=20
```

---

## 8. Заполнение БД тестовыми данными

Команда `python -m app.seed` создаёт:

- **12 городов**: MOW (Москва), LED (СПб), AER (Сочи), KZN, SVX, NSK, IST, DXB, LHR, CDG, BCN, JFK
- **140 рейсов**: 20 маршрутов × 7 дней вперёд, разные авиакомпании
- **Демо-пользователь**: `demo@skyroutes.local` / `demo1234` (с правами админа)

```bash
# Стандартный запуск (добавляет недостающие данные)
python -m app.seed

# Если нужно пересоздать базу с нуля
rm travel.db
python -m app.seed
```

---

## 9. Запуск тестов

### pytest-тесты (59 тестов)

```bash
# Все тесты
pytest tests/ -v

# С покрытием
pytest tests/ -v --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_auth.py -v

# С выводом логов
pytest tests/ -v -s
```

### Интеграционный smoke-тест

Поднимает uvicorn, прогоняет все сценарии:

```bash
python scripts/test_api.py
```

### Запуск через Makefile

```bash
make test       # pytest
make test-api   # smoke-тест
```

---

## 10. Миграции БД через Alembic

После изменения моделей в `app/models.py`:

### Создание миграции

```bash
alembic revision --autogenerate -m "add new column"
```

В файле `alembic/versions/xxxx_add_new_column.py` проверьте изменения.

### Применение миграций

```bash
# Все неприменённые миграции
alembic upgrade head

# До конкретной ревизии
alembic upgrade <revision_id>

# Откатить последнюю
alembic downgrade -1

# Откатить до конкретной ревизии
alembic downgrade <revision_id>
```

### Просмотр статуса

```bash
alembic current    # текущая ревизия
alembic history    # история всех миграций
alembic heads      # головные ревизии
```

**Важно:** Alembic берёт URL БД из переменной `TRAVEL_DATABASE_URL` (см. `alembic/env.py`).

---

## 11. Запуск CI/CD через GitHub Actions

Файл `.github/workflows/ci.yml` запускается автоматически на push/PR в `main`/`master`.

### Что выполняется

1. Установка зависимостей на Python 3.11 и 3.12
2. Линтинг `ruff check app/ tests/ scripts/`
3. Проверка форматирования `black --check`
4. Запуск pytest (`sqlite+aiosqlite:///:memory:`)
5. Запуск интеграционного smoke-теста
6. Загрузка логов как артефактов

### Ручной запуск

1. Откройте вкладку **Actions** в GitHub-репозитории
2. Выберите workflow **CI**
3. Нажмите **Run workflow**

---

## 12. Настройка pre-commit хуков

Автоматическая проверка и форматирование кода перед каждым коммитом.

### Установка

```bash
pip install pre-commit
pre-commit install
```

### Что проверяется

- `ruff check --fix` — авто-исправление стиля
- `black` — форматирование
- `trailing-whitespace` — удаление лишних пробелов
- `end-of-file-fixer` — проверка конца файла
- `check-yaml` — валидация YAML
- `check-added-large-files` — защита от больших файлов
- `check-merge-conflict` — проверка конфликтов слияния
- `debug-statements` — поиск `breakpoint()` и `pdb`

### Запуск вручную

```bash
# На всех файлах
pre-commit run --all-files

# На конкретном файле
pre-commit run --files app/main.py
```

---

## 13. CLI-утилита manage.py

В проекте есть CLI-утилита `scripts/manage.py` для управления через командную строку.

### Создание администратора

```bash
python scripts/manage.py create-admin \
  --email admin@example.com \
  --password adminsecret \
  --name "Admin User"
```

### Создание обычного пользователя

```bash
python scripts/manage.py create-user \
  --email user@example.com \
  --password userpassword \
  --name "Regular User"
```

### Создание рейса

```bash
python scripts/manage.py create-flight \
  --number SU9999 \
  --airline "Аэрофлот" \
  --aircraft "Airbus A350" \
  --origin 1 \
  --dest 3 \
  --dep "2026-10-01T10:00" \
  --arr "2026-10-01T13:00" \
  --price 25000 \
  --seats 200
```

### Сводная статистика

```bash
python scripts/manage.py stats
```

Вывод:
```
=== Сводная статистика SkyRoutes ===

  Рейсы:           140 активных из 140
  Бронирования:    42 всего
    - pending:     5
    - confirmed:   30
    - cancelled:   7
  Выручка:         850000.00 ₽
    - в ожидании:  45000.00 ₽
  Пассажиры:       50
  Пользователи:    8
  Города:          12

=== Топ-5 популярных направлений ===

  1. MOW → AER: 15 броней, 120000 ₽
  ...
```

### Сброс базы данных

```bash
# С подтверждением
python scripts/manage.py reset-db

# Без подтверждения (для скриптов)
python scripts/manage.py reset-db --yes
```

### Экспорт OpenAPI спецификации

```bash
python scripts/manage.py export-openapi --output openapi.json
```

Полезно для генерации клиентов на других языках (TypeScript, Java, Go и т.д.) через
[openapi-generator](https://openapi-generator.tech/).

### Список всех маршрутов

```bash
python scripts/manage.py list-routes
```

Выводит все 53+ маршрутов API с HTTP-методами.

### Помощь

```bash
python scripts/manage.py --help
python scripts/manage.py create-admin --help
```

---

## 14. Нагрузочное тестирование (locust)

Для проверки производительности проекта используется [locust](https://locust.io/).

### Установка

```bash
pip install locust
```

### Запуск с веб-интерфейсом

```bash
# Сначала запусти приложение
python run.py &

# Запусти locust (откроется на http://localhost:8089)
locust -f scripts/locustfile.py --host http://localhost:8000
```

В веб-интерфейсе задай:
- Number of users: 50
- Spawn rate: 5 (пользователей в секунду)
- Host: http://localhost:8000

### Запуск в headless-режиме

```bash
locust -f scripts/locustfile.py \
    --headless \
    --host http://localhost:8000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 60s
```

### С CSV-отчётом

```bash
locust -f scripts/locustfile.py \
    --headless \
    --host http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 2m \
    --csv results
```

Создаст файлы: `results_stats.csv`, `results_stats_history.csv`, `results_failures.csv`.

### Сценарии в locustfile.py

Файл `scripts/locustfile.py` содержит 2 класса пользователей:

1. **`SkyRoutesUser`** — имитирует залогиненного пользователя:
   - Просмотр главной, поиска, городов
   - 30% шанс залогиниться как `demo@skyroutes.local`
   - Просмотр своих броней, избранного, статистики
   - Случайные фильтры и сортировки

2. **`AnonymousBrowser`** (вес 2×) — просто листает страницы:
   - Главная, поиск, about, login, register

### Ожидаемые метрики (FastAPI + SQLite, обычный ноутбук)

| Метрика | Целевое значение |
|---|---|
| RPS | 200-500 запросов/сек |
| P50 latency | < 50ms |
| P95 latency | < 200ms |
| P99 latency | < 500ms |
| Failures | < 1% |

Для более тяжёлой нагрузки используй PostgreSQL и Gunicorn с 4+ workers:

```bash
gunicorn app.main:app -c gunicorn_conf.py -w 4 -k uvicorn.workers.UvicornWorker
```

---

## 15. Dark mode

В проекте есть переключатель темы (светлая/тёмная) — кнопка ☀/☾ в правом верхнем углу шапки.

### Как работает

- **CSS-переменные** в `:root` и `:root[data-theme="dark"]`
- Кнопка `<button id="themeToggle">` в `base.html`
- JavaScript в `app.js` переключает `data-theme` и сохраняет выбор в `localStorage`
- Inline-скрипт в `<head>` применяет тему **до рендера**, чтобы избежать FOUC (flash of unstyled content)
- Автоопределение системной темы через `window.matchMedia('(prefers-color-scheme: dark)')`

### Тестирование

1. Открой любую страницу
2. Нажми кнопку ☀ (или ☾) в правом верхнем углу
3. Тема должна переключиться мгновенно, без перезагрузки
4. Перезагрузи страницу — тема должна сохраниться
5. Измени системную тему — при первом заходе подхватится автоматически

### Кастомизация

Цвета тем настраиваются в `app/static/style.css`:

```css
:root {
    --bg: #f5f7fb;
    --surface: #ffffff;
    --primary: #1f5fff;
    /* ... */
}

:root[data-theme="dark"] {
    --bg: #0e1726;
    --surface: #1a2236;
    --primary: #4d80ff;
    /* ... */
}
```

---

## 16. Решение проблем (Troubleshooting)

### Проблема: `ModuleNotFoundError: No module named 'slowapi'`

**Решение:** Не установлены зависимости. Выполните:
```bash
pip install -r requirements.txt
```

### Проблема: `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL`

**Причина:** Неверный формат `DATABASE_URL`.

**Решение:** Используйте полный формат:
```env
# SQLite
TRAVEL_DATABASE_URL=sqlite+aiosqlite:///./travel.db

# PostgreSQL
TRAVEL_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# НЕ ИСПОЛЬЗУЙТЕ форматы типа:
# DATABASE_URL=file:/path/to/db  ← это невалидно
```

### Проблема: `bcrypt` не устанавливается на macOS с M1/M2

**Решение:** Установите `cryptography` сначала:
```bash
brew install openssl
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
pip install bcrypt
```

Или используйте версию 4.x (уже включает бинарники):
```bash
pip install bcrypt==4.2.0
```

### Проблема: Порт 8000 уже занят

**Решение:** Используйте другой порт:
```bash
uvicorn app.main:app --port 8080
# или
BIND=0.0.0.0:8080 docker compose up
```

### Проблема: `asyncpg` не подключается к PostgreSQL

**Проверьте:**
1. PostgreSQL запущен: `pg_isready -h localhost -p 5432`
2. БД и пользователь созданы (см. [Шаг 2](#шаг-2-создание-бд-и-пользователя))
3. `pg_hba.conf` разрешает подключения (для локальных подключений должен быть `trust` или `md5`)
4. Брандмауэр не блокирует порт 5432

### Проблема: Тесты падают с `RuntimeError: Event loop is closed`

**Решение:** Обновите pytest-asyncio:
```bash
pip install --upgrade pytest-asyncio
```

### Проблема: Docker не запускается на Linux

```bash
# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
# Выйдите и зайдите снова
newgrp docker
```

### Проблема: Не приходят email (если добавили отправку)

Проверьте SMTP-настройки через:
```bash
python -c "
import smtplib
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login('you@gmail.com', 'app-password')
    print('OK')
"
```

### Полезные команды для диагностики

```bash
# Проверка состояния БД
sqlite3 travel.db ".tables"
sqlite3 travel.db "SELECT COUNT(*) FROM flights;"

# Проверка API
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/detailed

# Просмотр логов
docker compose logs -f app
tail -f /var/log/skyroutes.log

# Список запущенных процессов
ps aux | grep uvicorn
```

---

## Демо-аккаунты

После `python -m app.seed`:

| Email | Пароль | Роль |
|---|---|---|
| `demo@skyroutes.local` | `demo1234` | администратор |

Зарегистрировать обычного пользователя можно через `/register` или API:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword","full_name":"You"}'
```

---

## Где что лежит

| URL | Назначение |
|---|---|
| http://localhost:8000 | Главная страница |
| http://localhost:8000/flights | Поиск рейсов (с сортировкой) |
| http://localhost:8000/login | Вход |
| http://localhost:8000/register | Регистрация |
| http://localhost:8000/reset | Сброс пароля (новое!) |
| http://localhost:8000/profile | Профиль пользователя |
| http://localhost:8000/favorites | Избранные рейсы |
| http://localhost:8000/my-bookings | Мои бронирования |
| http://localhost:8000/search-history | История поиска |
| http://localhost:8000/admin | Админ-панель с графиками (для admin) |
| http://localhost:8000/admin/audit | Аудит-лог действий (новое!) |
| http://localhost:8000/about | О проекте |
| http://localhost:8000/docs | Swagger UI (REST API) |
| http://localhost:8000/api/health | Health-check |
| http://localhost:8000/api/health/detailed | Health-check с зависимостями |
| http://localhost:8000/api/metrics | Метрики запросов |
| http://localhost:8000/api/admin/charts/bookings-by-day | Данные графика бронирований |
| http://localhost:8000/api/admin/charts/avg-prices | Средние цены по направлениям |
| http://localhost:8000/api/admin/charts/status-breakdown | Распределение по статусам |
| http://localhost:8000/api/admin/audit | Аудит-лог через API (новое!) |

---

## Поддержка

Если возникли проблемы:

1. Проверьте [Troubleshooting](#13-решение-проблем-troubleshooting)
2. Запустите `python scripts/test_api.py` — он покажет, что именно не работает
3. Изучите логи приложения (`docker compose logs app`)
4. Откройте issue на GitHub с описанием проблемы, логом и шагами воспроизведения

Удачи в путешествиях! ✈
