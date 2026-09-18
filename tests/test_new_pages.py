"""Тесты новых страниц: profile, favorites (HTML), search-history (HTML), booking actions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_user
from app.models import City, Flight


async def _seed_flight(db: AsyncSession) -> int:
    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="AER", name="Сочи", country="Россия")
    db.add_all([origin, dest])
    await db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flight = Flight(
        flight_number="PAG01",
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
    db.add(flight)
    await db.commit()
    return flight.id


@pytest.mark.asyncio
async def test_profile_page_requires_auth(client):
    """Профиль без логина — редирект на /login."""
    r = await client.get("/profile", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


@pytest.mark.asyncio
async def test_profile_page_with_auth(client, db_session: AsyncSession):
    """Профиль с логином — 200 и содержит данные пользователя."""
    await create_user(
        db_session,
        email="profile@example.com",
        password="password123",
        full_name="Profile User",
    )
    await db_session.commit()

    # Логинимся через API
    r = await client.post(
        "/api/auth/login",
        data={"username": "profile@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]

    # Запрашиваем профиль с токеном через cookie
    r = await client.get(
        "/profile",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "Profile User" in r.text
    assert "profile@example.com" in r.text


@pytest.mark.asyncio
async def test_favorites_page_requires_auth(client):
    r = await client.get("/favorites", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


@pytest.mark.asyncio
async def test_favorites_page_with_auth(client, db_session: AsyncSession):
    """Страница избранного с залогиненным пользователем — 200."""
    await create_user(
        db_session,
        email="favpage@example.com",
        password="password123",
        full_name="Fav Page",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "favpage@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]

    r = await client.get(
        "/favorites",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "Избранное" in r.text or "избран" in r.text.lower()


@pytest.mark.asyncio
async def test_search_history_page_requires_auth(client):
    r = await client.get("/search-history", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


@pytest.mark.asyncio
async def test_search_history_page_with_auth(client, db_session: AsyncSession):
    await create_user(
        db_session,
        email="sh@example.com",
        password="password123",
        full_name="SH User",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "sh@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]

    r = await client.get(
        "/search-history",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "История" in r.text or "истории" in r.text.lower()


@pytest.mark.asyncio
async def test_favorites_add_via_html_form(client, db_session: AsyncSession):
    """Добавление в избранное через HTML-форму."""
    flight_id = await _seed_flight(db_session)
    await create_user(
        db_session,
        email="favform@example.com",
        password="password123",
        full_name="Fav Form",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "favform@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]

    r = await client.post(
        f"/favorites/{flight_id}/add",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/favorites" in r.headers["location"]


@pytest.mark.asyncio
async def test_favorites_remove_via_html_form(client, db_session: AsyncSession):
    flight_id = await _seed_flight(db_session)
    await create_user(
        db_session,
        email="favrm@example.com",
        password="password123",
        full_name="Fav Rm",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "favrm@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]

    # Сначала добавляем
    await client.post(
        f"/favorites/{flight_id}/add",
        cookies={"access_token": token},
        follow_redirects=False,
    )

    # Удаляем
    r = await client.post(
        f"/favorites/{flight_id}/remove",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/favorites" in r.headers["location"]


@pytest.mark.asyncio
async def test_booking_confirm_action(client, db_session: AsyncSession):
    """Подтверждение бронирования через HTML-форму."""
    flight_id = await _seed_flight(db_session)
    await create_user(
        db_session,
        email="conf@example.com",
        password="password123",
        full_name="Confirm User",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "conf@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Создаём бронирование
    r = await client.post(
        "/api/bookings",
        headers=headers,
        json={
            "flight_id": flight_id,
            "contact_email": "conf@example.com",
            "contact_phone": "+79991234567",
            "passengers": [
                {
                    "first_name": "Test",
                    "last_name": "User",
                    "birth_date": "1990-01-01",
                    "passport_number": "12345678",
                    "cabin_class": "economy",
                }
            ],
        },
    )
    code = r.json()["code"]

    # Подтверждаем через HTML-форму
    r = await client.post(
        f"/booking/{code}/confirm",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303

    # Проверяем, что статус изменился
    r = await client.get(f"/api/bookings/{code}", headers=headers)
    assert r.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_booking_cancel_action(client, db_session: AsyncSession):
    """Отмена бронирования через HTML-форму."""
    flight_id = await _seed_flight(db_session)
    await create_user(
        db_session,
        email="cancel@example.com",
        password="password123",
        full_name="Cancel User",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/login",
        data={"username": "cancel@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/bookings",
        headers=headers,
        json={
            "flight_id": flight_id,
            "contact_email": "cancel@example.com",
            "contact_phone": "+79991234567",
            "passengers": [
                {
                    "first_name": "Test",
                    "last_name": "User",
                    "birth_date": "1990-01-01",
                    "passport_number": "12345678",
                    "cabin_class": "economy",
                }
            ],
        },
    )
    code = r.json()["code"]

    r = await client.post(
        f"/booking/{code}/cancel",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = await client.get(f"/api/bookings/{code}", headers=headers)
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_health_detailed_endpoint(client):
    """Детальный health-check с проверкой БД."""
    r = await client.get("/api/health/detailed")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert data["dependencies"]["database"]["status"] == "ok"
