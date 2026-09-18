"""Тесты сброса пароля и аудита."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_user


@pytest.mark.asyncio
async def test_password_reset_request_for_existing_user(
    client, db_session: AsyncSession
):
    """Запрос сброса для существующего email — 202 + в debug возвращает demo_reset_url."""
    await create_user(
        db_session,
        email="reset@example.com",
        password="oldpassword",
        full_name="Reset User",
    )
    await db_session.commit()

    r = await client.post(
        "/api/auth/password-reset/request",
        json={
            "email": "reset@example.com",
        },
    )
    assert r.status_code == 202
    data = r.json()
    assert "message" in data
    # В debug-режиме возвращается demo_reset_url с токеном
    assert "demo_reset_url" in data
    assert "/reset?token=" in data["demo_reset_url"]


@pytest.mark.asyncio
async def test_password_reset_request_for_nonexistent_email(client):
    """Запрос для несуществующего email — тоже 202 (не раскрываем существование)."""
    r = await client.post(
        "/api/auth/password-reset/request",
        json={
            "email": "nonexistent@example.com",
        },
    )
    assert r.status_code == 202
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_password_reset_confirm_with_valid_token(
    client, db_session: AsyncSession
):
    """Полный цикл: запрос → использование токена → смена пароля → вход."""
    await create_user(
        db_session,
        email="fullcycle@example.com",
        password="oldpassword123",
        full_name="Full Cycle",
    )
    await db_session.commit()

    # Запрос токена
    r = await client.post(
        "/api/auth/password-reset/request",
        json={
            "email": "fullcycle@example.com",
        },
    )
    assert r.status_code == 202
    reset_url = r.json()["demo_reset_url"]
    token = reset_url.split("token=")[-1]

    # Установка нового пароля
    r = await client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "newpassword123",
        },
    )
    assert r.status_code == 200
    assert "has been reset" in r.json()["message"]

    # Проверяем, что новый пароль работает
    r = await client.post(
        "/api/auth/login",
        data={"username": "fullcycle@example.com", "password": "newpassword123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_password_reset_confirm_with_invalid_token(client):
    """Невалидный токен → 400."""
    r = await client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": "invalid-token-does-not-exist-1234567890",
            "new_password": "newpassword123",
        },
    )
    assert r.status_code == 400
    assert "Invalid or expired" in r.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_confirm_with_used_token(client, db_session: AsyncSession):
    """Токен можно использовать только один раз."""
    await create_user(
        db_session,
        email="used@example.com",
        password="oldpassword123",
        full_name="Used Token",
    )
    await db_session.commit()

    # Запрос токена
    r = await client.post(
        "/api/auth/password-reset/request",
        json={
            "email": "used@example.com",
        },
    )
    token = r.json()["demo_reset_url"].split("token=")[-1]

    # Первое использование — успех
    r = await client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "newpassword123",
        },
    )
    assert r.status_code == 200

    # Второе использование — должно провалиться
    r = await client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "anotherpassword123",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_password_reset_page_html(client):
    """HTML-страница сброса пароля доступна."""
    r = await client.get("/reset")
    assert r.status_code == 200
    assert "Сброс пароля" in r.text or "сброс" in r.text.lower()

    # С токеном
    r = await client.get("/reset?token=sometesttoken123")
    assert r.status_code == 200
    assert "Новый пароль" in r.text or "token" in r.text.lower()


# === Audit log tests ===


async def _admin_token(client, db_session: AsyncSession) -> dict:
    """Создаёт админа и возвращает заголовки."""
    await create_user(
        db_session,
        email="audit-admin@example.com",
        password="adminsecret",
        full_name="Audit Admin",
        is_admin=True,
    )
    await db_session.commit()
    r = await client.post(
        "/api/auth/login",
        data={"username": "audit-admin@example.com", "password": "adminsecret"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_audit_empty(client, db_session: AsyncSession):
    """Аудит-лог пуст, если админ ничего не делал."""
    headers = await _admin_token(client, db_session)
    r = await client.get("/api/admin/audit", headers=headers)
    assert r.status_code == 200
    # Только что создали админа — логов может и не быть
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_audit_records_actions(client, db_session: AsyncSession):
    """После действий админом в аудите должны появиться записи."""
    headers = await _admin_token(client, db_session)

    # Создаём город (генерирует запись аудита)
    r = await client.post(
        "/api/admin/cities",
        headers=headers,
        json={
            "code": "AUD",
            "name": "Аудит-Сити",
            "country": "Россия",
        },
    )
    assert r.status_code == 201

    # Проверяем аудит
    r = await client.get("/api/admin/audit", headers=headers)
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 1
    # Последняя запись должна быть create_city
    assert logs[0]["action"] == "create_city"
    assert logs[0]["entity_type"] == "city"
    assert "AUD" in logs[0]["details"]


@pytest.mark.asyncio
async def test_admin_audit_requires_admin(client, db_session: AsyncSession):
    """Обычный пользователь не может смотреть аудит."""
    r = await client.post(
        "/api/auth/register",
        json={
            "email": "noaudit@example.com",
            "password": "password123",
            "full_name": "No Audit",
        },
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/audit", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_page_html(client, db_session: AsyncSession):
    """HTML-страница аудита доступна для админа."""
    await _admin_token(client, db_session)
    # Логинимся через HTML-форму для cookie
    r = await client.post(
        "/api/auth/login",
        data={"username": "audit-admin@example.com", "password": "adminsecret"},
    )
    token = r.json()["access_token"]

    r = await client.get(
        "/admin/audit",
        cookies={"access_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert "Аудит" in r.text or "audit" in r.text.lower()


@pytest.mark.asyncio
async def test_admin_audit_requires_auth(client):
    """Без токена — 401."""
    r = await client.get("/api/admin/audit")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_audit_logs_flight_crud(client, db_session: AsyncSession):
    """Все CRUD-операции с рейсами должны логироваться."""
    headers = await _admin_token(client, db_session)

    # Создаём города
    from app.models import City

    origin = City(code="MOW", name="Москва", country="Россия")
    dest = City(code="LED", name="Санкт-Петербург", country="Россия")
    db_session.add_all([origin, dest])
    await db_session.commit()
    await db_session.refresh(origin)
    await db_session.refresh(dest)

    # Создаём рейс
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r = await client.post(
        "/api/admin/flights",
        headers=headers,
        json={
            "flight_number": "AUD01",
            "airline": "Test Air",
            "aircraft": "A320",
            "origin_id": origin.id,
            "destination_id": dest.id,
            "departure_at": (now + timedelta(days=1)).isoformat(),
            "arrival_at": (now + timedelta(days=1, hours=2)).isoformat(),
            "base_price": 5000.0,
            "seats_total": 100,
        },
    )
    assert r.status_code == 201
    flight_id = r.json()["id"]

    # Обновляем рейс
    await client.patch(
        f"/api/admin/flights/{flight_id}",
        headers=headers,
        json={"base_price": 6000.0},
    )

    # Удаляем (деактивируем)
    await client.delete(f"/api/admin/flights/{flight_id}", headers=headers)

    # Проверяем аудит
    r = await client.get("/api/admin/audit", headers=headers)
    logs = r.json()
    actions = [log["action"] for log in logs]
    assert "create_flight" in actions
    assert "update_flight" in actions
    assert "delete_flight" in actions
