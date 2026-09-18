"""Тесты аутентификации: регистрация, логин, /me."""

import pytest


@pytest.mark.asyncio
async def test_register(client):
    r = await client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "supersecret",
            "full_name": "Alice Liddell",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data and data["access_token"]
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["full_name"] == "Alice Liddell"
    assert data["user"]["is_admin"] is False


@pytest.mark.asyncio
async def test_register_duplicate(client):
    payload = {
        "email": "bob@example.com",
        "password": "supersecret",
        "full_name": "Bob",
    }
    await client.post("/api/auth/register", json=payload)
    r = await client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "carol@example.com",
            "password": "supersecret",
            "full_name": "Carol",
        },
    )
    r = await client.post(
        "/api/auth/login",
        data={"username": "carol@example.com", "password": "supersecret"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "dave@example.com",
            "password": "correct-password",
            "full_name": "Dave",
        },
    )
    r = await client.post(
        "/api/auth/login",
        data={"username": "dave@example.com", "password": "wrong-password"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "eve@example.com",
            "password": "supersecret",
            "full_name": "Eve",
        },
    )
    token = reg.json()["access_token"]
    r = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "eve@example.com"
