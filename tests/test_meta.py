"""Тесты мета-эндпоинтов и базового API."""
import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "SkyRoutes" in data["app"]


@pytest.mark.asyncio
async def test_api_root(client):
    r = await client.get("/api")
    assert r.status_code == 200
    endpoints = r.json()["endpoints"]
    assert "auth" in endpoints
    assert "flights_search" in endpoints
    assert "cities" in endpoints


@pytest.mark.asyncio
async def test_cities_empty(client):
    r = await client.get("/api/cities")
    assert r.status_code == 200
    assert r.json() == []
