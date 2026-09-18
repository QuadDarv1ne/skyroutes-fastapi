# Contributing to SkyRoutes

Спасибо, что хотите внести вклад в SkyRoutes! Этот документ описывает процесс разработки и правила.

## 🚀 Быстрый старт для контрибьюторов

### 1. Форк и клонирование

```bash
# Форкните репозиторий на GitHub, затем:
git clone https://github.com/your-username/skyroutes.git
cd skyroutes
git remote add upstream https://github.com/original/skyroutes.git
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
pip install pre-commit
pre-commit install
```

### 3. Запуск тестов

```bash
# Перед каждым коммитом убеждаемся, что тесты проходят
pytest tests/ -v

# Интеграционный smoke-тест
python scripts/test_api.py
```

### 4. Создание ветки для фичи

```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/issue-123-description
```

## 📋 Правила разработки

### Стиль кода

Проект использует **ruff** для линтинга и **black** для форматирования:

```bash
# Проверка стиля
ruff check app/ tests/ scripts/

# Авто-исправление
ruff check --fix app/ tests/ scripts/

# Форматирование
black app/ tests/ scripts/
```

Конфигурация в `pyproject.toml`. Pre-commit хуки автоматически запускают эти инструменты перед каждым коммитом.

### Именование

- **Файлы Python**: `snake_case.py`
- **Классы**: `PascalCase` (напр. `FlightRead`)
- **Функции и переменные**: `snake_case` (напр. `get_flight_by_id`)
- **Константы**: `UPPER_SNAKE_CASE` (напр. `CABIN_MULTIPLIER`)
- **HTML-шаблоны**: `snake_case.html`
- **CSS-классы**: `kebab-case` (напр. `flight-card`)

### Структура коммитов

Используем [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Типы:**
- `feat` — новая функция
- `fix` — исправление бага
- `docs` — только документация
- `style` — форматирование, без изменения логики
- `refactor` — рефакторинг без новой функциональности
- `test` — добавление или исправление тестов
- `chore` — сборка, зависимости, конфиги

**Примеры:**
```
feat(auth): add password reset flow

- New model PasswordResetToken
- /api/auth/password-reset/request and /confirm endpoints
- HTML page /reset with form

Closes #123
```

```
fix(admin): handle missing flight_id in audit log
```

## 🧪 Тестирование

### Покрытие тестами

Все новые функции должны сопровождаться тестами:

```bash
# Запуск с покрытием
pytest tests/ -v --cov=app --cov-report=term-missing

# Цель: > 80% покрытия для новых модулей
```

### Структура тестов

- `tests/test_<module>.py` — тесты для `app/<module>.py`
- Имена функций: `test_<scenario>`, например `test_register_duplicate_email_returns_409`
- Используйте фикстуры из `conftest.py`
- Каждый тест должен быть независимым

### Существующие категории тестов

| Файл | Что покрывает |
|---|---|
| `test_meta.py` | health, root API |
| `test_auth.py` | регистрация, логин, /me |
| `test_flights.py` | поиск, фильтры рейсов |
| `test_bookings.py` | создание, отмена броней |
| `test_admin.py` | admin CRUD и статистика |
| `test_pagination.py` | пагинация и сортировка |
| `test_pages.py` | HTML-страницы, 404 |
| `test_favorites.py` | избранное |
| `test_metrics.py` | метрики, история поиска |
| `test_new_pages.py` | profile, confirm/cancel |
| `test_charts.py` | аналитика графиков |

## 🏗 Архитектурные принципы

### 1. Разделение слоёв

- **`models.py`** — только ORM-модели SQLAlchemy
- **`schemas.py`** — только Pydantic-схемы для API
- **`crud.py`** — бизнес-логика, обращение к БД
- **`routers/`** — HTTP-обработчики, тонкий слой
- **`security.py`** — JWT, bcrypt, зависимости

### 2. Async-first

Все обращения к БД — асинхронные (через `AsyncSession`). Не используйте синхронный SQLAlchemy.

### 3. Зависимости FastAPI

Используйте `Depends()` для:
- `get_db` — сессия БД
- `get_current_user` — текущий пользователь (или None)
- `require_user` — обязательно залогинен
- `require_admin` — обязательно админ

### 4. Обработка ошибок

- `404` — ресурс не найден
- `401` — неавторизован
- `403` — нет прав
- `409` — конфликт (дубликат)
- `422` — невалидные данные (Pydantic)
- `500` — внутренняя ошибка (логируется)

Используйте `HTTPException` с понятным `detail`.

### 5. Миграции БД

При изменении `models.py` создавай миграцию:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Проверь сгенерированную миграцию в `alembic/versions/` перед коммитом.

## 🎨 UI/UX принципы

### CSS

- Используй CSS-переменные из `:root` (`--primary`, `--text`, `--bg` и т.д.)
- Dark mode: тестируй в обеих темах — добавляй стили в `:root[data-theme="dark"]` при необходимости
- Mobile-first: сначала стили для мобильных, потом `@media (min-width: ...)` для десктопа

### JavaScript

- Vanilla JS, без фреймворков (кроме Chart.js на admin-странице)
- Каждый блок оборачивай в IIFE: `(function() { ... })();`
- Не засоряй глобальную область видимости

### HTML-шаблоны

- Наследование через `{% extends "base.html" %}`
- Блоки: `{% block title %}`, `{% block content %}`
- Контекст: всегда передавай `settings` и `current_user`

## 📝 Pull Request процесс

1. **Создай PR** с понятным заголовком и описанием
2. **Привяжи issue** (если есть) через `Closes #123`
3. **Проверь checklist**:
   - [ ] Тесты проходят локально
   - [ ] Добавлены тесты для новой функциональности
   - [ ] Документация обновлена (README, API.md, CHANGELOG.md)
   - [ ] Стиль кода соответствует ruff/black
   - [ ] Нет merge-конфликтов с `main`
4. **Жди ревью** — ответим в течение 2-3 дней
5. **Внеси правки** по результатам ревью

### Шаблон описания PR

```markdown
## Что делает этот PR
Краткое описание изменений.

## Тип изменения
- [ ] Bug fix (fix)
- [ ] Новая функция (feat)
- [ ] Breaking change
- [ ] Документация

## Как тестировать
1. ...
2. ...

## Скриншоты (если UI)
Before / After

## Checklist
- [ ] Код следует стилю проекта
- [ ] Саморевью выполнено
- [ ] Тесты добавлены и проходят
- [ ] Документация обновлена
```

## 🐛 Отчёты об ошибках

Используй GitHub Issues. Включи:

1. **Описание** — что произошло
2. **Шаги воспроизведения** — как повторить
3. **Ожидаемое поведение** — что должно было произойти
4. **Скриншот / логи** — если применимо
5. **Окружение**:
   - OS: (напр. Ubuntu 22.04)
   - Python: (напр. 3.12.14)
   - Версия SkyRoutes: (напр. 0.6.0)
   - БД: (напр. SQLite)

## 💬 Контакты

- **Issues**: GitHub Issues
- **Обсуждения**: GitHub Discussions
- **Email**: support@skyroutes.local (демо)

## 📄 Лицензия

Внося вклад, ты соглашаешься, что твой код будет опубликован под [MIT License](LICENSE).

---

Спасибо за вклад в SkyRoutes! ✈
