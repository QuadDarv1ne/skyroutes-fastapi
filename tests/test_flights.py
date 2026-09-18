"""Тесты городов и рейсов."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import get_cities, get_flights
from app.models import City, Flight
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_create_city(db_session: AsyncSession):
    city = City(code="MOW", name="Москва", country="Россия", timezone="Europe/Moscow")
    db_session.add(city)
    await db_session.commit()

    cities = await get_cities(db_session)
    assert len(cities) == 1
    assert cities[0].code == "MOW"


@pytest.mark.asyncio
async def test_create_flight(db_session: AsyncSession):
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="LED", name="Санкт-Петербург", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="SU1234",
        airline="Аэрофлот",
        aircraft="Airbus A321",
        origin_id=origin.id,
        destination_id=dest.id,
        departure_at=now,
        arrival_at=now + timedelta(hours=2),
        duration_minutes=120,
        base_price=4500.0,
        seats_total=180,
        seats_available=180,
    )
    db_session.add(flight)
    await db_session.commit()

    flights = await get_flights(db_session, origin_code="MOW", destination_code="LED")
    assert len(flights) == 1
    assert flights[0].flight_number == "SU1234"


@pytest.mark.asyncio
async def test_flights_filter_by_price(db_session: AsyncSession):
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add_all(
        [
            Flight(
                flight_number="SU1",
                airline="X",
                aircraft="A320",
                origin_id=origin.id,
                destination_id=dest.id,
                departure_at=now,
                arrival_at=now + timedelta(hours=3),
                duration_minutes=180,
                base_price=5000.0,
                seats_total=180,
                seats_available=180,
            ),
            Flight(
                flight_number="SU2",
                airline="Y",
                aircraft="B737",
                origin_id=origin.id,
                destination_id=dest.id,
                departure_at=now,
                arrival_at=now + timedelta(hours=3),
                duration_minutes=180,
                base_price=15000.0,
                seats_total=180,
                seats_available=180,
            ),
        ]
    )
    await db_session.commit()

    cheap = await get_flights(
        db_session, origin_code="MOW", destination_code="AER", max_price=10000
    )
    assert len(cheap) == 1
    assert cheap[0].flight_number == "SU1"
