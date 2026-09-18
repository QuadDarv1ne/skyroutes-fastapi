"""Тесты избранных рейсов пользователя."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Flight


async def _seed_flight(db: AsyncSession) -> int:
    """Создаёт тестовый рейс, возвращает flight_id."""
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db.add_all([origin, dest])
    await db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="FAV01",
        airline="Test Air",
        aircraft="A320",
        origin_id=origin.id,
        destination_id=dest.id,
        departure_at=now,
        arrival_at=now + timedelta(hours=3),
        duration_minutes=180,
        base_price=5000.0,
        seats_total=180,
        seats_available=180,
    )
    db.add(flight)
    await db.commit()
    return flight.id


@pytest.mark.asyncio
async def test_favorites_requires_auth(client):
    r = await client.get("/api/favorites")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_add_and_list_favorite(client, db_session: AsyncSession):
    flight_id = await _seed_flight(db_session)

    # Регистрируем пользователя
    r = await client.post("/api/auth/register", json={
        "email": "fav@example.com",
        "password": "favpass123",
        "full_name": "Fav User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Сначала избранное пусто
    r = await client.get("/api/favorites", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    # Добавляем в избранное
    r = await client.post(f"/api/favorites/{flight_id}", headers=headers)
    assert r.status_code == 201

    # Проверяем, что появился в списке
    r = await client.get("/api/favorites", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == flight_id


@pytest.mark.asyncio
async def test_add_favorite_duplicate(client, db_session: AsyncSession):
    flight_id = await _seed_flight(db_session)
    r = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
        "full_name": "Dup User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Первое добавление — 201
    r = await client.post(f"/api/favorites/{flight_id}", headers=headers)
    assert r.status_code == 201

    # Второе — 409 (уже в избранном)
    r = await client.post(f"/api/favorites/{flight_id}", headers=headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_add_favorite_nonexistent_flight(client):
    r = await client.post("/api/auth/register", json={
        "email": "miss@example.com",
        "password": "password123",
        "full_name": "Miss User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/favorites/99999", headers=headers)
    assert r.status_code == 409  # рейс не найден → 409 по контракту


@pytest.mark.asyncio
async def test_remove_favorite(client, db_session: AsyncSession):
    flight_id = await _seed_flight(db_session)
    r = await client.post("/api/auth/register", json={
        "email": "remove@example.com",
        "password": "password123",
        "full_name": "Remove User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Добавляем
    await client.post(f"/api/favorites/{flight_id}", headers=headers)

    # Удаляем
    r = await client.delete(f"/api/favorites/{flight_id}", headers=headers)
    assert r.status_code == 204

    # Проверяем, что списка пуст
    r = await client.get("/api/favorites", headers=headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_remove_nonexistent_favorite(client):
    r = await client.post("/api/auth/register", json={
        "email": "rm-miss@example.com",
        "password": "password123",
        "full_name": "Rm Miss",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.delete("/api/favorites/99999", headers=headers)
    assert r.status_code == 404
