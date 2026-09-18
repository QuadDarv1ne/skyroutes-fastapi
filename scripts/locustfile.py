"""Нагрузочное тестирование SkyRoutes через locust.

Запуск:
    # 1. Установка locust
    pip install locust

    # 2. Запуск теста (откроется веб-интерфейс на http://localhost:8089)
    locust -f scripts/locustfile.py

    # 3. Без веб-интерфейса (headless):
    locust -f scripts/locustfile.py \
        --headless \
        --host http://localhost:8000 \
        --users 50 \
        --spawn-rate 5 \
        --run-time 60s

    # 4. С CSV-отчётом:
    locust -f scripts/locustfile.py \
        --headless \
        --host http://localhost:8000 \
        --users 100 \
        --spawn-rate 10 \
        --run-time 2m \
        --csv results
"""

from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def _random_email() -> str:
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"loadtest_{name}@example.com"


class SkyRoutesUser(HttpUser):
    """Имитация обычного пользователя SkyRoutes."""

    # Пауза между запросами: 1-3 секунды (как реальный пользователь)
    wait_time = between(1, 3)

    def on_start(self):
        """При старте регистрируемся или логинимся как демо."""
        # 30% шанс залогиниться как demo-пользователь
        if random.random() < 0.3:
            r = self.client.post(
                "/api/auth/login",
                data={"username": "demo@skyroutes.local", "password": "demo1234"},
                name="POST /api/auth/login",
            )
            if r.status_code == 200:
                self.token = r.json().get("access_token")
                self.auth_headers = {"Authorization": f"Bearer {self.token}"}
                return

        self.token = None
        self.auth_headers = {}

    @task(5)
    def view_homepage(self):
        """Главная страница — самая частая операция."""
        self.client.get("/", name="GET / (home)")

    @task(4)
    def search_flights(self):
        """Поиск рейсов с разными фильтрами."""
        params = {
            "limit": 10,
            "sort_by": random.choice(
                ["departure_at", "base_price", "duration_minutes"]
            ),
            "sort_order": random.choice(["asc", "desc"]),
        }
        # 50% шанс добавить фильтры
        if random.random() < 0.5:
            params["origin"] = random.choice(["MOW", "LED", "AER"])
            params["destination"] = random.choice(["AER", "MOW", "LED", "DXB"])
        self.client.get("/api/flights", params=params, name="GET /api/flights (search)")

    @task(3)
    def view_cities(self):
        """Получение списка городов."""
        self.client.get("/api/cities", name="GET /api/cities")

    @task(2)
    def view_flights_page(self):
        """HTML-страница поиска."""
        self.client.get("/flights", name="GET /flights (HTML)")

    @task(2)
    def view_about(self):
        """Страница About."""
        self.client.get("/about", name="GET /about")

    @task(2)
    def view_health(self):
        """Health-check."""
        self.client.get("/api/health", name="GET /api/health")

    @task(1)
    def view_flight_detail(self):
        """Детали случайного рейса (1-20)."""
        flight_id = random.randint(1, 20)
        self.client.get(
            f"/api/flights/{flight_id}",
            name="GET /api/flights/{id}",
        )

    @task(1)
    def view_my_bookings_if_logged_in(self):
        """Если залогинен — смотрим свои брони."""
        if self.token:
            self.client.get(
                "/api/bookings",
                headers=self.auth_headers,
                name="GET /api/bookings (my bookings)",
            )

    @task(1)
    def view_favorites_if_logged_in(self):
        """Если залогинен — смотрим избранное."""
        if self.token:
            self.client.get(
                "/api/favorites",
                headers=self.auth_headers,
                name="GET /api/favorites",
            )

    @task(1)
    def view_admin_stats_if_admin(self):
        """Если залогинен как demo (admin) — смотрим статистику."""
        if self.token:
            self.client.get(
                "/api/admin/stats",
                headers=self.auth_headers,
                name="GET /api/admin/stats",
            )


class AnonymousBrowser(HttpUser):
    """Имитация анонимного посетителя, который просто смотрит страницы."""

    wait_time = between(2, 5)
    weight = 2  # в 2 раза больше, чем залогиненных

    @task
    def browse(self):
        page = random.choice(["/", "/flights", "/about", "/login", "/register"])
        self.client.get(page, name=f"GET {page} (anonymous)")


# === Пример ожидаемых результатов ===
#
# Запуск на localhost:
#   locust -f scripts/locustfile.py --headless --host http://localhost:8000 \
#       --users 50 --spawn-rate 5 --run-time 60s
#
# Ожидаемые метрики (FastAPI + SQLite, обычный ноутбук):
#   - RPS: 200-500 запросов/сек
#   - P50 latency: < 50ms
#   - P95 latency: < 200ms
#   - P99 latency: < 500ms
#   - Failures: < 1%
#
# Для более тяжёлой нагрузки используйте PostgreSQL и Gunicorn с 4+ workers.
