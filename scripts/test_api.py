"""Скрипт интеграционного тестирования API.

Сам поднимает uvicorn, прогоняет все сценарии, выводит отчёт.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8000"
PROJECT = Path(__file__).resolve().parent.parent


def wait_for_server(timeout: int = 30) -> bool:
    for _ in range(timeout * 4):
        try:
            r = requests.get(f"{BASE}/api/health", timeout=0.5)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.25)
    return False


def main():
    # Поднимаем uvicorn
    env = os.environ.copy()
    env["TRAVEL_DATABASE_URL"] = "sqlite+aiosqlite:///./travel_test.db"
    env["TRAVEL_DEBUG"] = "False"

    test_db = PROJECT / "travel_test.db"
    if test_db.exists():
        test_db.unlink()

    proc = subprocess.Popen(
        [str(PROJECT / ".venv/bin/uvicorn"), "app.main:app",
         "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=str(PROJECT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        print("⏳ Waiting for server...")
        if not wait_for_server():
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"❌ Server did not start.\nstderr: {stderr}")
            sys.exit(1)
        print("✅ Server is up\n")

        # Заполняем БД
        subprocess.run(
            [str(PROJECT / ".venv/bin/python"), "-m", "app.seed"],
            cwd=str(PROJECT), env=env, check=True,
            capture_output=True,
        )

        all_ok = True

        def check(name, condition):
            nonlocal all_ok
            ok = "✅" if condition else "❌"
            print(f"  {ok} {name}")
            if not condition:
                all_ok = False

        print("=== Health ===")
        r = requests.get(f"{BASE}/api/health")
        check("health 200", r.status_code == 200)

        print("\n=== HTML pages ===")
        for path in ["/", "/login", "/register", "/my-bookings", "/flights",
                     "/booking/1", "/about", "/contacts", "/docs"]:
            r = requests.get(f"{BASE}{path}", allow_redirects=False)
            check(f"GET {path:25} → 200", r.status_code == 200)

        print("\n=== 404 handling ===")
        r = requests.get(f"{BASE}/nonexistent", headers={"Accept": "text/html"})
        check("HTML 404 returns 404", r.status_code == 404)
        check("HTML 404 contains '404'", "404" in r.text)

        r = requests.get(f"{BASE}/api/nonexistent")
        check("API 404 returns JSON", r.status_code == 404 and "detail" in r.json())

        print("\n=== Register duplicate (409) ===")
        requests.post(f"{BASE}/api/auth/register", json={
            "email": "tester@example.com", "password": "tester1234", "full_name": "T"
        })
        r = requests.post(f"{BASE}/api/auth/register", json={
            "email": "tester@example.com", "password": "tester1234", "full_name": "T"
        })
        check("duplicate 409", r.status_code == 409)

        print("\n=== Login as demo admin ===")
        r = requests.post(
            f"{BASE}/api/auth/login",
            data={"username": "demo@skyroutes.local", "password": "demo1234"},
        )
        check("demo login 200", r.status_code == 200)
        token = r.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {token}"}

        print("\n=== /api/auth/me ===")
        r = requests.get(f"{BASE}/api/auth/me", headers=admin_headers)
        check("me 200", r.status_code == 200)
        check("me is_admin True", r.json().get("is_admin") is True)

        print("\n=== Flights search + sorting ===")
        r = requests.get(f"{BASE}/api/flights", params={
            "origin": "MOW", "destination": "AER", "limit": 5,
            "sort_by": "base_price", "sort_order": "asc",
        })
        check("flights search 200", r.status_code == 200)
        flights = r.json()
        check("flights found > 0", len(flights) > 0)
        if flights:
            prices = [f["base_price"] for f in flights]
            check("sorted by price asc", prices == sorted(prices))

        print("\n=== Admin: stats ===")
        r = requests.get(f"{BASE}/api/admin/stats", headers=admin_headers)
        check("stats 200", r.status_code == 200)
        stats = r.json()
        check("stats has flights_total", "flights_total" in stats)
        check("stats has revenue_total", "revenue_total" in stats)

        print("\n=== Admin: stats extended ===")
        r = requests.get(f"{BASE}/api/admin/stats/extended", headers=admin_headers)
        check("extended stats 200", r.status_code == 200)
        extended = r.json()
        check("has popular_routes", "popular_routes" in extended)
        check("has top_airlines", "top_airlines" in extended)

        print("\n=== Admin: create flight ===")
        cities = requests.get(f"{BASE}/api/cities").json()
        mow_id = next(c["id"] for c in cities if c["code"] == "MOW")
        aer_id = next(c["id"] for c in cities if c["code"] == "AER")
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        dep = (now + timedelta(days=10)).isoformat()
        arr = (now + timedelta(days=10, hours=3)).isoformat()
        r = requests.post(f"{BASE}/api/admin/flights", headers=admin_headers, json={
            "flight_number": "TEST01",
            "airline": "Test Air",
            "aircraft": "B777",
            "origin_id": mow_id,
            "destination_id": aer_id,
            "departure_at": dep,
            "arrival_at": arr,
            "base_price": 9999.0,
            "seats_total": 200,
        })
        check("create flight 201", r.status_code == 201)
        new_flight_id = r.json()["id"] if r.status_code == 201 else None

        print("\n=== Admin: update flight ===")
        if new_flight_id:
            r = requests.patch(
                f"{BASE}/api/admin/flights/{new_flight_id}",
                headers=admin_headers,
                json={"base_price": 12000.0, "is_active": False},
            )
            check("update flight 200", r.status_code == 200)
            check("price updated", r.json().get("base_price") == 12000.0)

        print("\n=== Admin: delete (deactivate) flight ===")
        if new_flight_id:
            r = requests.delete(
                f"{BASE}/api/admin/flights/{new_flight_id}",
                headers=admin_headers,
            )
            check("delete flight 204", r.status_code == 204)

        print("\n=== Admin: create city ===")
        r = requests.post(f"{BASE}/api/admin/cities", headers=admin_headers, json={
            "code": "KRR", "name": "Краснодар", "country": "Россия",
        })
        check("create city 201", r.status_code == 201)

        print("\n=== Admin page (logged in) ===")
        # Логин через HTML-форму (cookie)
        s = requests.Session()
        s.post(f"{BASE}/login", data={
            "email": "demo@skyroutes.local", "password": "demo1234"
        }, allow_redirects=False)
        r = s.get(f"{BASE}/admin", allow_redirects=False)
        check("admin page 200 for admin user", r.status_code == 200)
        check("admin page shows stats",
              "Рейсы" in r.text or "Выручка" in r.text or "flights" in r.text.lower())

        print("\n=== Booking workflow ===")
        r = requests.get(f"{BASE}/api/flights", params={"limit": 1})
        if r.json():
            fid = r.json()[0]["id"]
            r = requests.post(
                f"{BASE}/api/bookings",
                headers=admin_headers,
                json={
                    "flight_id": fid,
                    "contact_email": "tester@example.com",
                    "contact_phone": "+79991234567",
                    "passengers": [{
                        "first_name": "Alice", "last_name": "Wonder",
                        "birth_date": "1990-01-01", "passport_number": "12345678",
                        "cabin_class": "business",
                    }],
                },
            )
            check("create booking 201", r.status_code == 201)
            if r.status_code == 201:
                code = r.json()["code"]
                r = requests.get(f"{BASE}/api/bookings/{code}", headers=admin_headers)
                check("get booking 200", r.status_code == 200)
                r = requests.patch(
                    f"{BASE}/api/bookings/{code}", headers=admin_headers,
                    json={"status": "cancelled"}
                )
                check("cancel 200", r.status_code == 200)

        print("\n=== Unauthorized access ===")
        r = requests.get(f"{BASE}/api/bookings")
        check("no token → 401", r.status_code == 401)
        r = requests.get(f"{BASE}/api/admin/stats")
        check("admin no token → 401", r.status_code == 401)

        print("\n=== Admin page without login (403) ===")
        r = requests.get(f"{BASE}/admin", allow_redirects=False)
        check("admin page no login → 403", r.status_code == 403)

        print("\n=== Metrics endpoint ===")
        r = requests.get(f"{BASE}/api/metrics")
        check("metrics 200", r.status_code == 200)
        check("metrics has request_counts", "request_counts" in r.json())

        print("\n=== X-Total-Count header ===")
        r = requests.get(f"{BASE}/api/flights", params={"limit": 2})
        check("X-Total-Count header present",
              "X-Total-Count" in r.headers)
        total = int(r.headers.get("X-Total-Count", 0))
        check("X-Total-Count > 0", total > 0)

        print("\n=== Favorites workflow ===")
        flights_list = requests.get(f"{BASE}/api/flights", params={"limit": 1}).json()
        if flights_list:
            fid = flights_list[0]["id"]

            # Сначала избранное пусто
            r = requests.get(f"{BASE}/api/favorites", headers=admin_headers)
            check("favorites list empty", r.json() == [])

            # Добавляем
            r = requests.post(f"{BASE}/api/favorites/{fid}", headers=admin_headers)
            check("add favorite 201", r.status_code == 201)

            # Проверяем что появился
            r = requests.get(f"{BASE}/api/favorites", headers=admin_headers)
            check("favorites has 1 item", len(r.json()) == 1)

            # Дубликат → 409
            r = requests.post(f"{BASE}/api/favorites/{fid}", headers=admin_headers)
            check("duplicate favorite 409", r.status_code == 409)

            # Удаляем
            r = requests.delete(f"{BASE}/api/favorites/{fid}", headers=admin_headers)
            check("remove favorite 204", r.status_code == 204)

            # Проверяем, что списка пуст
            r = requests.get(f"{BASE}/api/favorites", headers=admin_headers)
            check("favorites empty after delete", r.json() == [])

        print("\n=== Favorites requires auth ===")
        r = requests.get(f"{BASE}/api/favorites")
        check("favorites no token → 401", r.status_code == 401)

        print("\n=== Search history ===")
        # Делаем поиск с фильтрами
        r = requests.get(f"{BASE}/api/flights", params={
            "origin": "MOW", "destination": "AER",
        }, headers=admin_headers)
        check("filtered search 200", r.status_code == 200)

        # Проверяем историю
        r = requests.get(f"{BASE}/api/search-history", headers=admin_headers)
        check("search-history 200", r.status_code == 200)
        check("search history has entries", len(r.json()) > 0)

        print("\n=== Search history requires auth ===")
        r = requests.get(f"{BASE}/api/search-history")
        check("search-history no token → 401", r.status_code == 401)

        print("\n=== Detailed health-check ===")
        r = requests.get(f"{BASE}/api/health/detailed")
        check("health/detailed 200", r.status_code == 200)
        data = r.json()
        check("has dependencies", "dependencies" in data)
        check("database status ok",
              data.get("dependencies", {}).get("database", {}).get("status") == "ok")

        print("\n=== Profile page (HTML) ===")
        # Логинимся через HTML-форму
        s = requests.Session()
        s.post(f"{BASE}/login", data={
            "email": "demo@skyroutes.local", "password": "demo1234"
        }, allow_redirects=False)

        r = s.get(f"{BASE}/profile", allow_redirects=False)
        check("profile page 200", r.status_code == 200)
        check("profile shows email", "demo@skyroutes.local" in r.text)

        print("\n=== Favorites page (HTML) ===")
        r = s.get(f"{BASE}/favorites", allow_redirects=False)
        check("favorites page 200", r.status_code == 200)

        print("\n=== Search history page (HTML) ===")
        r = s.get(f"{BASE}/search-history", allow_redirects=False)
        check("search-history page 200", r.status_code == 200)

        print("\n=== Booking confirm/cancel via HTML form ===")
        # Создаём бронирование
        flights_list = requests.get(f"{BASE}/api/flights", params={"limit": 1}).json()
        if flights_list:
            fid = flights_list[0]["id"]
            r = requests.post(
                f"{BASE}/api/bookings",
                headers=admin_headers,
                json={
                    "flight_id": fid,
                    "contact_email": "demo@skyroutes.local",
                    "contact_phone": "+79991234567",
                    "passengers": [{
                        "first_name": "Test", "last_name": "User",
                        "birth_date": "1990-01-01", "passport_number": "12345678",
                        "cabin_class": "economy",
                    }],
                },
            )
            if r.status_code == 201:
                code = r.json()["code"]

                # Подтверждаем через HTML-форму
                r = s.post(f"{BASE}/booking/{code}/confirm", allow_redirects=False)
                check("confirm booking 303", r.status_code == 303)

                # Проверяем статус
                r = requests.get(
                    f"{BASE}/api/bookings/{code}", headers=admin_headers
                )
                check("booking confirmed", r.json().get("status") == "confirmed")

                # Отменяем
                r = s.post(f"{BASE}/booking/{code}/cancel", allow_redirects=False)
                check("cancel booking 303", r.status_code == 303)

                r = requests.get(
                    f"{BASE}/api/bookings/{code}", headers=admin_headers
                )
                check("booking cancelled", r.json().get("status") == "cancelled")

        print("\n" + "=" * 50)
        print("RESULT:", "✅ ALL PASSED" if all_ok else "❌ SOME TESTS FAILED")
        print("=" * 50)
        sys.exit(0 if all_ok else 1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
