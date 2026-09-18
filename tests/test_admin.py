"""Тесты админ-API и статистики."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_user
from app.models import City, Flight


async def _seed_admin(db: AsyncSession) -> int:
    """Создаёт админа через db_session и возвращает его id."""
    user = await create_user(
        db,
        email="admin@example.com",
        password="adminsecret",
        full_name="Admin Root",
        is_admin=True,
    )
    await db.commit()
    return user.id


async def _admin_token(client, db: AsyncSession) -> dict:
    """Регистрирует админа и возвращает заголовки с токеном."""
    await _seed_admin(db)
    r = await client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "adminsecret"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _regular_token(client) -> dict:
    r = await client.post("/api/auth/register", json={
        "email": "user@example.com",
        "password": "usersecret",
        "full_name": "Regular User",
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_cities_and_flight(db: AsyncSession) -> int:
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="LED", name="Санкт-Петербург", country="Россия")
    db.add_all([origin, dest])
    await db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="TEST99",
        airline="Test Air",
        aircraft="B737",
        origin_id=origin.id,
        destination_id=dest.id,
        departure_at=now + timedelta(days=1),
        arrival_at=now + timedelta(days=1, hours=2),
        duration_minutes=120,
        base_price=10000.0,
        seats_total=100,
        seats_available=100,
    )
    db.add(flight)
    await db.commit()
    return flight.id


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client, db_session: AsyncSession):
    headers = await _regular_token(client)
    r = await client.get("/api/admin/stats", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_requires_auth(client):
    r = await client.get("/api/admin/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_empty(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/stats", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["flights_total"] == 0
    assert data["bookings_total"] == 0
    assert data["revenue_total"] == 0.0


@pytest.mark.asyncio
async def test_admin_create_flight(client, db_session: AsyncSession):
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.commit()
    await db_session.refresh(origin)
    await db_session.refresh(dest)

    headers = await _admin_token(client, db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r = await client.post("/api/admin/flights", headers=headers, json={
        "flight_number": "SU9999",
        "airline": "Аэрофлот",
        "aircraft": "Airbus A350",
        "origin_id": origin.id,
        "destination_id": dest.id,
        "departure_at": (now + timedelta(days=2)).isoformat(),
        "arrival_at": (now + timedelta(days=2, hours=3)).isoformat(),
        "base_price": 25000.0,
        "seats_total": 250,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["flight_number"] == "SU9999"
    assert data["base_price"] == 25000.0
    assert data["seats_available"] == 250


@pytest.mark.asyncio
async def test_admin_create_flight_validation(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # arrival before departure — должна пройти Pydantic-валидацию, но дать 400
    r = await client.post("/api/admin/flights", headers=headers, json={
        "flight_number": "BAD1",
        "airline": "Test Airline",
        "aircraft": "A320",
        "origin_id": 1,
        "destination_id": 2,
        "departure_at": (now + timedelta(days=2)).isoformat(),
        "arrival_at": (now + timedelta(days=1)).isoformat(),
        "base_price": 1000.0,
        "seats_total": 100,
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_update_flight(client, db_session: AsyncSession):
    flight_id = await _seed_cities_and_flight(db_session)
    headers = await _admin_token(client, db_session)

    r = await client.patch(
        f"/api/admin/flights/{flight_id}",
        headers=headers,
        json={"base_price": 15000.0, "is_active": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["base_price"] == 15000.0
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_delete_flight(client, db_session: AsyncSession):
    flight_id = await _seed_cities_and_flight(db_session)
    headers = await _admin_token(client, db_session)

    r = await client.delete(f"/api/admin/flights/{flight_id}", headers=headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_admin_create_city(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    r = await client.post("/api/admin/cities", headers=headers, json={
        "code": "KRR",
        "name": "Краснодар",
        "country": "Россия",
    })
    assert r.status_code == 201, r.text
    assert r.json()["code"] == "KRR"


@pytest.mark.asyncio
async def test_admin_stats_extended(client, db_session: AsyncSession):
    await _seed_cities_and_flight(db_session)
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/stats/extended", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "basic" in data
    assert "popular_routes" in data
    assert "top_airlines" in data
