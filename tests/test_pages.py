"""Тесты статических страниц и кастомных обработчиков ошибок."""
import pytest


@pytest.mark.asyncio
async def test_about_page(client):
    r = await client.get("/about")
    assert r.status_code == 200
    assert "О проекте" in r.text or "SkyRoutes" in r.text


@pytest.mark.asyncio
async def test_contacts_page(client):
    r = await client.get("/contacts")
    assert r.status_code == 200
    assert "Контакты" in r.text or "support" in r.text


@pytest.mark.asyncio
async def test_404_html(client):
    """Кастомная страница 404 для HTML-запроса."""
    r = await client.get("/nonexistent-page", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "404" in r.text


@pytest.mark.asyncio
async def test_404_json(client):
    """JSON-ответ 404 для API-запроса."""
    r = await client.get("/api/nonexistent-endpoint")
    assert r.status_code == 404
    data = r.json()
    assert data["status_code"] == 404
    assert "detail" in data


@pytest.mark.asyncio
async def test_admin_page_requires_auth(client):
    """Админ-страница без логина — 403."""
    r = await client.get("/admin", follow_redirects=False)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_flight_not_found_json(client):
    r = await client.get("/api/flights/99999")
    assert r.status_code == 404
    assert "detail" in r.json()
