"""Тесты пагинации и сортировки рейсов."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import City, Flight


async def _seed_multiple_flights(db: AsyncSession, count: int = 15) -> list[int]:
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db.add_all([origin, dest])
    await db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ids = []
    for i in range(count):
        f = Flight(
            flight_number=f"T{i:04d}",
            airline=f"Airline {i % 3}",
            aircraft="A320",
            origin_id=origin.id,
            destination_id=dest.id,
            departure_at=now + timedelta(hours=i),
            arrival_at=now + timedelta(hours=i + 2),
            duration_minutes=120 + i * 5,
            base_price=5000.0 + i * 500,
            seats_total=180,
            seats_available=180 - i,
        )
        db.add(f)
        await db.flush()
        ids.append(f.id)
    await db.commit()
    return ids


@pytest.mark.asyncio
async def test_pagination_limit_offset(client, db_session: AsyncSession):
    await _seed_multiple_flights(db_session, count=10)

    r = await client.get("/api/flights?limit=3&offset=0")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r2 = await client.get("/api/flights?limit=3&offset=3")
    assert r2.status_code == 200
    assert len(r2.json()) == 3
    # Разные рейсы
    assert r.json()[0]["id"] != r2.json()[0]["id"]


@pytest.mark.asyncio
async def test_sort_by_price_asc(client, db_session: AsyncSession):
    await _seed_multiple_flights(db_session, count=5)
    r = await client.get("/api/flights?sort_by=base_price&sort_order=asc&limit=5")
    prices = [f["base_price"] for f in r.json()]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_sort_by_price_desc(client, db_session: AsyncSession):
    await _seed_multiple_flights(db_session, count=5)
    r = await client.get("/api/flights?sort_by=base_price&sort_order=desc&limit=5")
    prices = [f["base_price"] for f in r.json()]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.asyncio
async def test_sort_by_duration(client, db_session: AsyncSession):
    await _seed_multiple_flights(db_session, count=5)
    r = await client.get("/api/flights?sort_by=duration_minutes&sort_order=desc")
    durations = [f["duration_minutes"] for f in r.json()]
    assert durations == sorted(durations, reverse=True)


@pytest.mark.asyncio
async def test_invalid_sort_field_returns_422(client, db_session: AsyncSession):
    """Несуществующее поле сортировки — 422 (валидация Literal)."""
    await _seed_multiple_flights(db_session, count=3)
    r = await client.get("/api/flights?sort_by=invalid_field&sort_order=asc")
    assert r.status_code == 422
