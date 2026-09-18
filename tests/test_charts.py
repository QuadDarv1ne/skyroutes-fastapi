"""Тесты аналитических эндпоинтов админ-API (для графиков)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_user
from app.models import City, Flight


async def _admin_token(client, db: AsyncSession) -> dict:
    await create_user(
        db,
        email="chart-admin@example.com",
        password="adminsecret",
        full_name="Chart Admin",
        is_admin=True,
    )
    await db.commit()
    r = await client.post(
        "/api/auth/login",
        data={"username": "chart-admin@example.com", "password": "adminsecret"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_charts_bookings_by_day_empty(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/charts/bookings-by-day", headers=headers)
    assert r.status_code == 200
    assert r.json() == []  # нет броней


@pytest.mark.asyncio
async def test_charts_avg_prices_empty(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/charts/avg-prices", headers=headers)
    assert r.status_code == 200
    assert r.json() == []  # нет рейсов


@pytest.mark.asyncio
async def test_charts_avg_prices_with_flights(client, db_session: AsyncSession):
    """Создаём города и рейсы, проверяем avg-prices."""
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(3):
        db_session.add(Flight(
            flight_number=f"AP{i:03d}",
            airline="Test Air",
            aircraft="A320",
            origin_id=origin.id,
            destination_id=dest.id,
            departure_at=now + timedelta(days=i + 1),
            arrival_at=now + timedelta(days=i + 1, hours=2),
            duration_minutes=120,
            base_price=5000.0 + i * 1000,
            seats_total=180,
            seats_available=180,
        ))
    await db_session.commit()

    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/charts/avg-prices", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1  # один маршрут
    assert data[0]["origin_code"] == "MOW"
    assert data[0]["destination_code"] == "AER"
    assert data[0]["flights_count"] == 3
    assert data[0]["min_price"] == 5000.0
    assert data[0]["max_price"] == 7000.0
    # avg = (5000+6000+7000)/3 = 6000
    assert abs(data[0]["avg_price"] - 6000.0) < 0.01


@pytest.mark.asyncio
async def test_charts_status_breakdown_empty(client, db_session: AsyncSession):
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/charts/status-breakdown", headers=headers)
    assert r.status_code == 200
    assert r.json() == {}  # нет броней


@pytest.mark.asyncio
async def test_charts_status_breakdown_with_bookings(client, db_session: AsyncSession):
    """С бронированиями должен вернуть распределение."""
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="LED", name="Санкт-Петербург", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="SB01",
        airline="Test Air",
        aircraft="A320",
        origin_id=origin.id,
        destination_id=dest.id,
        departure_at=now + timedelta(days=1),
        arrival_at=now + timedelta(days=1, hours=2),
        duration_minutes=120,
        base_price=5000.0,
        seats_total=180,
        seats_available=180,
    )
    db_session.add(flight)
    await db_session.commit()

    headers = await _admin_token(client, db_session)

    # Создаём бронирования разных статусов
    r = await client.post("/api/bookings", headers=headers, json={
        "flight_id": flight.id,
        "contact_email": "sb1@example.com",
        "contact_phone": "+79991234567",
        "passengers": [{
            "first_name": "A", "last_name": "B",
            "birth_date": "1990-01-01", "passport_number": "12345678",
            "cabin_class": "economy",
        }],
    })
    assert r.status_code == 201
    code1 = r.json()["code"]

    r = await client.post("/api/bookings", headers=headers, json={
        "flight_id": flight.id,
        "contact_email": "sb2@example.com",
        "contact_phone": "+79991234567",
        "passengers": [{
            "first_name": "C", "last_name": "D",
            "birth_date": "1990-01-01", "passport_number": "12345678",
            "cabin_class": "economy",
        }],
    })
    code2 = r.json()["code"]

    # Первую подтверждаем
    await client.patch(f"/api/bookings/{code1}", headers=headers, json={"status": "confirmed"})
    # Вторую отменяем
    await client.patch(f"/api/bookings/{code2}", headers=headers, json={"status": "cancelled"})

    r = await client.get("/api/admin/charts/status-breakdown", headers=headers)
    assert r.status_code == 200
    breakdown = r.json()
    assert breakdown.get("confirmed", 0) >= 1
    assert breakdown.get("cancelled", 0) >= 1


@pytest.mark.asyncio
async def test_charts_endpoints_require_admin(client, db_session: AsyncSession):
    """Обычный пользователь не может получить аналитику."""
    r = await client.post("/api/auth/register", json={
        "email": "regular@example.com",
        "password": "password123",
        "full_name": "Regular User",
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/charts/bookings-by-day", headers=headers)
    assert r.status_code == 403

    r = await client.get("/api/admin/charts/avg-prices", headers=headers)
    assert r.status_code == 403

    r = await client.get("/api/admin/charts/status-breakdown", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_charts_endpoints_require_auth(client):
    """Без токена — 401."""
    r = await client.get("/api/admin/charts/bookings-by-day")
    assert r.status_code == 401
