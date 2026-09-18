# API документация SkyRoutes

Полное описание REST API сервиса поиска и бронирования авиабилетов.

📖 **Интерактивная документация**: http://localhost:8000/docs (Swagger UI)
📖 **ReDoc**: http://localhost:8000/redoc

## Содержание

- [Аутентификация](#аутентификация)
- [Cities (Города)](#cities-города)
- [Flights (Рейсы)](#flights-рейсы)
- [Bookings (Бронирования)](#bookings-бронирования)
- [Favorites (Избранное)](#favorites-избранное)
- [Search History (История поиска)](#search-history-история-поиска)
- [Admin (Админ-API)](#admin-админ-api)
- [Meta (Метаданные)](#meta-метаданные)

---

## Аутентификация

Все защищённые эндпоинты требуют JWT-токен в заголовке:
```
Authorization: Bearer <access_token>
```

Токен действителен 24 часа (настраивается через `TRAVEL_ACCESS_TOKEN_EXPIRE_MINUTES`).

### POST /api/auth/register

Регистрация нового пользователя.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "Иван Иванов"
}
```

**Ответ 201:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов",
    "is_admin": false,
    "created_at": "2026-09-17T10:00:00"
  }
}
```

**Ошибки:**
- `409` — email уже зарегистрирован
- `422` — невалидный email или короткий пароль (< 8 символов)

### POST /api/auth/login

Вход по email и паролю. Использует OAuth2PasswordRequestForm.

**Тело запроса (form-data):**
```
username=user@example.com
password=password123
```

**Ответ 200:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "...", "is_admin": false, ... }
}
```

**Ошибки:**
- `401` — неверный email или пароль

### GET /api/auth/me

Текущий пользователь по JWT-токену.

**Заголовок:** `Authorization: Bearer <token>`

**Ответ 200:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "is_admin": false,
  "created_at": "2026-09-17T10:00:00"
}
```

**Ошибки:** `401` — неавторизован

---

## Cities (Города)

### GET /api/cities

Список всех городов.

**Ответ 200:**
```json
[
  { "id": 1, "code": "MOW", "name": "Москва", "country": "Россия", "timezone": "Europe/Moscow" },
  { "id": 2, "code": "LED", "name": "Санкт-Петербург", "country": "Россия", "timezone": "Europe/Moscow" }
]
```

---

## Flights (Рейсы)

### GET /api/flights

Поиск рейсов с фильтрами, сортировкой и пагинацией.

**Параметры запроса:**

| Параметр | Тип | Описание |
|---|---|---|
| `origin` | string | IATA-код вылета (напр. `MOW`) |
| `destination` | string | IATA-код прилёта (напр. `AER`) |
| `date_from` | date | Дата вылета с (включительно), формат `YYYY-MM-DD` |
| `date_to` | date | Дата вылета по (включительно) |
| `max_price` | float | Максимальная базовая цена |
| `airline` | string | Подстрока в названии авиакомпании |
| `min_seats` | int | Минимум свободных мест (по умолч. 1) |
| `sort_by` | enum | `departure_at` / `base_price` / `duration_minutes` |
| `sort_order` | enum | `asc` / `desc` |
| `limit` | int | Кол-во результатов (1-100, по умолч. из `PAGE_SIZE`) |
| `offset` | int | Смещение для пагинации |

**Заголовки ответа:**
- `X-Total-Count` — общее число рейсов по фильтрам
- `X-Page-Size` — размер страницы
- `X-Page-Offset` — текущее смещение

**Пример:**
```bash
curl "http://localhost:8000/api/flights?origin=MOW&destination=AER&sort_by=base_price&sort_order=asc&limit=5"
```

**Ответ 200:**
```json
[
  {
    "id": 8,
    "flight_number": "S71007",
    "airline": "S7 Airlines",
    "aircraft": "Airbus A320",
    "origin": { "id": 1, "code": "MOW", "name": "Москва", "country": "Россия" },
    "destination": { "id": 3, "code": "AER", "name": "Сочи", "country": "Россия" },
    "departure_at": "2026-09-17T09:00:00",
    "arrival_at": "2026-09-17T12:30:00",
    "duration_minutes": 210,
    "base_price": 6800.0,
    "seats_available": 180,
    "is_active": true
  }
]
```

### GET /api/flights/{flight_id}

Детали конкретного рейса.

**Ответ 200:** как элемент массива выше.

**Ошибки:** `404` — рейс не найден

---

## Bookings (Бронирования)

### POST /api/bookings

Создать бронирование. Уменьшает кол-во доступных мест на рейсе.

**Заголовок:** `Authorization: Bearer <token>` (опционально, для привязки к пользователю)

**Тело запроса:**
```json
{
  "flight_id": 8,
  "contact_email": "user@example.com",
  "contact_phone": "+79991234567",
  "passengers": [
    {
      "first_name": "Иван",
      "last_name": "Иванов",
      "birth_date": "1990-05-12",
      "passport_number": "4510123456",
      "cabin_class": "business"
    }
  ]
}
```

**Классы обслуживания и множители цены:**
- `economy` × 1.0
- `premium` × 1.4
- `business` × 2.5
- `first` × 4.0

**Ответ 201:**
```json
{
  "id": 1,
  "code": "QRP5GK",
  "flight_id": 8,
  "user_id": 1,
  "contact_email": "user@example.com",
  "contact_phone": "+79991234567",
  "total_price": 17000.0,
  "status": "pending",
  "created_at": "2026-09-17T10:00:00",
  "passengers": [ ... ]
}
```

**Ошибки:**
- `409` — рейс не найден или нет мест
- `422` — невалидные данные

### GET /api/bookings/{code}

Найти бронирование по PNR-коду.

**Ответ 200:** как выше.

**Ошибки:** `404` — не найдено

### PATCH /api/bookings/{code}

Изменить статус бронирования.

**Заголовок:** `Authorization: Bearer <token>`

**Тело запроса:**
```json
{ "status": "confirmed" }
```

**Статусы:**
- `pending` — ожидает (по умолчанию)
- `confirmed` — подтверждено
- `cancelled` — отменено (места возвращаются в рейс)

**Ответ 200:** обновлённое бронирование.

### GET /api/bookings

Мои бронирования (требует JWT) или поиск по email.

**Заголовок:** `Authorization: Bearer <token>` (обязательно)

**Параметры:**
- `email` (опц.) — найти бронирования по контактному email

**Ответ 200:** `[ { ... }, ... ]`

---

## Favorites (Избранное)

### GET /api/favorites

Избранные рейсы текущего пользователя.

**Заголовок:** `Authorization: Bearer <token>`

**Ответ 200:** список объектов FlightRead.

### POST /api/favorites/{flight_id}

Добавить рейс в избранное.

**Заголовок:** `Authorization: Bearer <token>`

**Ответ 201:**
```json
{ "status": "added", "flight_id": 8 }
```

**Ошибки:**
- `409` — уже в избранном или рейс не найден

### DELETE /api/favorites/{flight_id}

Удалить рейс из избранного.

**Заголовок:** `Authorization: Bearer <token>`

**Ответ 204** (No Content).

**Ошибки:** `404` — не найдено в избранном

---

## Search History (История поиска)

### GET /api/search-history

История поисковых запросов текущего пользователя.

**Заголовок:** `Authorization: Bearer <token>`

**Параметры:**
- `limit` (опц.) — кол-во записей (1-50, по умолч. 10)

**Ответ 200:**
```json
[
  {
    "id": 1,
    "origin_code": "MOW",
    "destination_code": "AER",
    "date_from": "2026-09-20",
    "date_to": null,
    "max_price": null,
    "results_count": 7,
    "created_at": "2026-09-17T10:00:00"
  }
]
```

---

## Admin (Админ-API)

Все эндпоинты требуют JWT с `is_admin=True`. Иначе — `403`.

### Управление рейсами

#### POST /api/admin/flights

Создать новый рейс.

**Тело запроса:**
```json
{
  "flight_number": "SU9999",
  "airline": "Аэрофлот",
  "aircraft": "Airbus A350",
  "origin_id": 1,
  "destination_id": 3,
  "departure_at": "2026-09-25T10:00:00",
  "arrival_at": "2026-09-25T13:00:00",
  "base_price": 25000.0,
  "seats_total": 250,
  "is_active": true
}
```

**Ответ 201:** созданный рейс (FlightRead).

**Ошибки:**
- `400` — `arrival_at` раньше `departure_at` или одинаковые `origin_id` и `destination_id`

#### PATCH /api/admin/flights/{flight_id}

Обновить поля рейса (частично).

**Тело запроса (все поля опциональны):**
```json
{
  "base_price": 15000.0,
  "is_active": false,
  "aircraft": "Boeing 777"
}
```

**Ответ 200:** обновлённый рейс.

#### DELETE /api/admin/flights/{flight_id}

Деактивировать рейс (мягкое удаление, `is_active = false`).

**Ответ 204** (No Content).

### Управление городами

#### POST /api/admin/cities

Создать новый город.

**Тело запроса:**
```json
{
  "code": "KRR",
  "name": "Краснодар",
  "country": "Россия",
  "timezone": "Europe/Moscow"
}
```

**Ответ 201:** созданный город (CityRead).

### Статистика

#### GET /api/admin/stats

Сводные счётчики.

**Ответ 200:**
```json
{
  "flights_total": 140,
  "flights_active": 140,
  "bookings_total": 42,
  "bookings_pending": 5,
  "bookings_confirmed": 30,
  "bookings_cancelled": 7,
  "revenue_total": 850000.0,
  "revenue_pending": 45000.0,
  "passengers_total": 50,
  "users_total": 8,
  "cities_total": 12
}
```

#### GET /api/admin/stats/extended

Статистика + топ направлений + топ авиакомпаний.

**Ответ 200:**
```json
{
  "basic": { ... },  // как в /stats
  "popular_routes": [
    {
      "origin_code": "MOW",
      "origin_name": "Москва",
      "destination_code": "AER",
      "destination_name": "Сочи",
      "bookings_count": 15,
      "revenue": 120000.0
    }
  ],
  "top_airlines": [
    { "airline": "Аэрофлот", "bookings_count": 20, "revenue": 250000.0 }
  ]
}
```

### Аналитика для графиков

#### GET /api/admin/charts/bookings-by-day?days=14

Количество бронирований и выручка по дням.

**Ответ 200:**
```json
[
  { "date": "2026-09-17", "count": 5, "revenue": 50000.0 },
  { "date": "2026-09-18", "count": 3, "revenue": 28000.0 }
]
```

#### GET /api/admin/charts/avg-prices?limit=10

Средние/мин/макс цены по топ-N направлениям.

**Ответ 200:**
```json
[
  {
    "origin_code": "MOW",
    "origin_name": "Москва",
    "destination_code": "AER",
    "destination_name": "Сочи",
    "flights_count": 7,
    "avg_price": 5800.0,
    "min_price": 4200.0,
    "max_price": 6800.0
  }
]
```

#### GET /api/admin/charts/status-breakdown

Распределение бронирований по статусам (для pie chart).

**Ответ 200:**
```json
{
  "pending": 5,
  "confirmed": 30,
  "cancelled": 7
}
```

---

## Meta (Метаданные)

### GET /api/health

Простой health-check.

**Ответ 200:**
```json
{
  "status": "ok",
  "app": "SkyRoutes — Путешествия и Авиаперелёты",
  "version": "0.6.0"
}
```

### GET /api/health/detailed

Health-check с проверкой БД.

**Ответ 200:**
```json
{
  "status": "ok",
  "app": "SkyRoutes — Путешествия и Авиаперелёты",
  "version": "0.6.0",
  "dependencies": {
    "database": {
      "status": "ok",
      "error": null,
      "url": "sqlite+aiosqlite://***"
    }
  },
  "timestamp": 1747654321.123
}
```

Если БД недоступна: `"status": "degraded"`, `"database.status": "error"`.

### GET /api/metrics

In-memory счётчики запросов по `METHOD:STATUS`.

**Ответ 200:**
```json
{
  "request_counts": {
    "GET:200": 145,
    "POST:201": 8,
    "GET:404": 3,
    "POST:401": 1
  },
  "version": "0.6.0"
}
```

### GET /api

Корневой эндпоинт со списком всех доступных URL.

---

## Коды ошибок

| Код | Значение |
|---|---|
| 200 | OK — успешный запрос |
| 201 | Created — ресурс создан |
| 204 | No Content — успешное удаление |
| 400 | Bad Request — неверные параметры |
| 401 | Unauthorized — неавторизован |
| 403 | Forbidden — нет прав (нужен админ) |
| 404 | Not Found — ресурс не найден |
| 409 | Conflict — дубликат или конфликт |
| 422 | Unprocessable Entity — невалидные данные |
| 429 | Too Many Requests — превышен rate limit |
| 500 | Internal Server Error — серверная ошибка |

## Формат ошибок API

```json
{
  "detail": "Booking not found",
  "status_code": 404
}
```

## Rate limiting

По умолчанию 200 запросов в минуту на IP. При превышении — `429 Too Many Requests`.

## Content-Type

Все запросы и ответы — `application/json` (кроме HTML-страниц).
