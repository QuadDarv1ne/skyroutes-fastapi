"""Тесты бронирований: создание, просмотр, отмена."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Flight


async def _create_flight(db: AsyncSession) -> int:
    """Создаёт тестовый рейс, возвращает flight_id."""
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db.add_all([origin, dest])
    await db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="TEST01",
        airline="Test Air",
        aircraft="A320",
        origin_id=origin.id,
        destination_id=dest.id,
        departure_at=now,
        arrival_at=now + timedelta(hours=3),
        duration_minutes=180,
        base_price=5000.0,
        seats_total=10,
        seats_available=10,
    )
    db.add(flight)
    await db.commit()
    return flight.id


@pytest.mark.asyncio
async def test_create_booking(client, db_session: AsyncSession):
    flight_id = await _create_flight(db_session)
    r = await client.post(
        "/api/bookings",
        json={
            "flight_id": flight_id,
            "contact_email": "ivan@example.com",
            "contact_phone": "+79991234567",
            "passengers": [
                {
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "birth_date": "1990-05-12",
                    "passport_number": "4510123456",
                    "cabin_class": "economy",
                }
            ],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert len(data["code"]) == 6
    assert data["total_price"] == 5000.0
    assert data["status"] == "pending"
    assert len(data["passengers"]) == 1


@pytest.mark.asyncio
async def test_get_booking_by_code(client, db_session: AsyncSession):
    flight_id = await _create_flight(db_session)
    create = await client.post(
        "/api/bookings",
        json={
            "flight_id": flight_id,
            "contact_email": "alice@example.com",
            "contact_phone": "+79991234567",
            "passengers": [
                {
                    "first_name": "A",
                    "last_name": "B",
                    "birth_date": "2000-01-01",
                    "passport_number": "12345678",
                    "cabin_class": "business",
                }
            ],
        },
    )
    code = create.json()["code"]
    r = await client.get(f"/api/bookings/{code}")
    assert r.status_code == 200
    assert r.json()["code"] == code


@pytest.mark.asyncio
async def test_cancel_booking(client, db_session: AsyncSession):
    flight_id = await _create_flight(db_session)
    create = await client.post(
        "/api/bookings",
        json={
            "flight_id": flight_id,
            "contact_email": "bob@example.com",
            "contact_phone": "+79991234567",
            "passengers": [
                {
                    "first_name": "A",
                    "last_name": "B",
                    "birth_date": "2000-01-01",
                    "passport_number": "12345678",
                    "cabin_class": "economy",
                }
            ],
        },
    )
    code = create.json()["code"]
    r = await client.patch(f"/api/bookings/{code}", json={"status": "cancelled"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_my_bookings_requires_auth(client):
    r = await client.get("/api/bookings")
    assert r.status_code == 401
