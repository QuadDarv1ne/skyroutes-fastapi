"""Тесты метрик, rate limiting и истории поиска."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Flight


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    r = await client.get("/api/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "request_counts" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_metrics_counts_requests(client):
    # Делаем несколько запросов
    await client.get("/api/health")
    await client.get("/api/health")
    await client.get("/api/cities")

    r = await client.get("/api/metrics")
    counts = r.json()["request_counts"]
    # Хотя бы один счётчик с GET:200
    has_get_200 = any(k.startswith("GET:200") for k in counts.keys())
    assert has_get_200


@pytest.mark.asyncio
async def test_search_history_requires_auth(client):
    r = await client.get("/api/search-history")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_search_history_saved_after_search(client, db_session: AsyncSession):
    """При поиске с фильтрами история должна сохраняться."""
    # Создаём города и рейс
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add(
        Flight(
            flight_number="SH01",
            airline="Test Air",
            aircraft="A320",
            origin_id=origin.id,
            destination_id=dest.id,
            departure_at=now + timedelta(days=1),
            arrival_at=now + timedelta(days=1, hours=3),
            duration_minutes=180,
            base_price=5000.0,
            seats_total=180,
            seats_available=180,
        )
    )
    await db_session.commit()

    # Регистрируемся и логинимся
    r = await client.post(
        "/api/auth/register",
        json={
            "email": "search@example.com",
            "password": "password123",
            "full_name": "Searcher",
        },
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Делаем поиск с фильтрами с токеном пользователя
    r = await client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "AER", "limit": 5},
        headers=headers,
    )
    assert r.status_code == 200

    # Проверяем, что история появилась
    r = await client.get("/api/search-history", headers=headers)
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    assert history[0]["origin_code"] == "MOW"
    assert history[0]["destination_code"] == "AER"


@pytest.mark.asyncio
async def test_search_history_not_saved_without_filters(
    client, db_session: AsyncSession
):
    """Поиск без фильтров не должен сохраняться в истории."""
    r = await client.post(
        "/api/auth/register",
        json={
            "email": "no-filters@example.com",
            "password": "password123",
            "full_name": "No Filters",
        },
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Поиск без фильтров
    r = await client.get("/api/flights")
    assert r.status_code == 200

    # История должна быть пуста
    r = await client.get("/api/search-history", headers=headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_x_total_count_header(client, db_session: AsyncSession):
    """API flights возвращает X-Total-Count в заголовке."""
    # Создаём 3 рейса
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="LED", name="Санкт-Петербург", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(3):
        db_session.add(
            Flight(
                flight_number=f"TC{i:03d}",
                airline="Test",
                aircraft="A320",
                origin_id=origin.id,
                destination_id=dest.id,
                departure_at=now + timedelta(hours=i),
                arrival_at=now + timedelta(hours=i + 2),
                duration_minutes=120,
                base_price=5000.0 + i * 1000,
                seats_total=180,
                seats_available=180,
            )
        )
    await db_session.commit()

    r = await client.get("/api/flights", params={"limit": 2})
    assert r.status_code == 200
    assert r.headers.get("X-Total-Count") == "3"
    assert r.headers.get("X-Page-Size") == "2"
    assert r.headers.get("X-Page-Offset") == "0"
    assert len(r.json()) == 2  # только 2 из-за limit
