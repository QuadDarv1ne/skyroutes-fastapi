"""Заполнение БД тестовыми городами и рейсами.

Запуск:
    python -m app.seed
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models import City, Flight, User
from app.security import hash_password


CITIES = [
    {"code": "MOW", "name": "Москва", "country": "Россия", "timezone": "Europe/Moscow"},
    {
        "code": "LED",
        "name": "Санкт-Петербург",
        "country": "Россия",
        "timezone": "Europe/Moscow",
    },
    {"code": "AER", "name": "Сочи", "country": "Россия", "timezone": "Europe/Moscow"},
    {"code": "KZN", "name": "Казань", "country": "Россия", "timezone": "Europe/Moscow"},
    {
        "code": "SVX",
        "name": "Екатеринбург",
        "country": "Россия",
        "timezone": "Asia/Yekaterinburg",
    },
    {
        "code": "NSK",
        "name": "Новосибирск",
        "country": "Россия",
        "timezone": "Asia/Novosibirsk",
    },
    {
        "code": "IST",
        "name": "Стамбул",
        "country": "Турция",
        "timezone": "Europe/Istanbul",
    },
    {"code": "DXB", "name": "Дубай", "country": "ОАЭ", "timezone": "Asia/Dubai"},
    {
        "code": "LHR",
        "name": "Лондон",
        "country": "Великобритания",
        "timezone": "Europe/London",
    },
    {"code": "CDG", "name": "Париж", "country": "Франция", "timezone": "Europe/Paris"},
    {
        "code": "BCN",
        "name": "Барселона",
        "country": "Испания",
        "timezone": "Europe/Madrid",
    },
    {
        "code": "JFK",
        "name": "Нью-Йорк",
        "country": "США",
        "timezone": "America/New_York",
    },
]


# (откуда, куда, авиакомпания, борт, длительность_мин, базовая_цена, цена_дня_смещение)
ROUTES = [
    ("MOW", "LED", "Аэрофлот", "Airbus A321", 90, 4500),
    ("MOW", "AER", "S7 Airlines", "Airbus A320", 210, 6800),
    ("MOW", "AER", "Победа", "Boeing 737", 200, 4200),
    ("MOW", "KZN", "Аэрофлот", "Sukhoi Superjet 100", 110, 3900),
    ("MOW", "SVX", "Utair", "Boeing 737", 140, 5100),
    ("MOW", "NSK", "S7 Airlines", "Airbus A320", 240, 8200),
    ("LED", "MOW", "Аэрофлот", "Airbus A321", 95, 4300),
    ("LED", "AER", "Россия", "Airbus A319", 220, 6400),
    ("AER", "MOW", "S7 Airlines", "Airbus A320", 205, 6500),
    ("MOW", "IST", "Турецкие авиалинии", "Boeing 737", 195, 11500),
    ("IST", "MOW", "Турецкие авиалинии", "Boeing 737", 190, 11200),
    ("MOW", "DXB", "Emirates", "Boeing 777", 330, 24500),
    ("DXB", "MOW", "Emirates", "Boeing 777", 340, 23800),
    ("MOW", "LHR", "British Airways", "Airbus A350", 250, 28900),
    ("MOW", "CDG", "Air France", "Airbus A320", 220, 21500),
    ("CDG", "BCN", "Vueling", "Airbus A320", 110, 6200),
    ("IST", "DXB", "flydubai", "Boeing 737", 290, 9800),
    ("JFK", "LHR", "British Airways", "Boeing 787", 415, 45000),
    ("MOW", "BCN", "S7 Airlines", "Airbus A321", 270, 18500),
    ("NSK", "MOW", "Аэрофлот", "Airbus A320", 245, 8000),
]


async def seed() -> None:
    await init_db()

    async with async_session_factory() as session:
        # Города
        existing_cities = (await session.execute(select(City))).scalars().all()
        existing_codes = {c.code for c in existing_cities}

        cities_added: list[City] = []
        for c in CITIES:
            if c["code"] not in existing_codes:
                city = City(**c)
                session.add(city)
                cities_added.append(city)
        await session.flush()

        all_cities = (await session.execute(select(City))).scalars().all()
        by_code = {c.code: c.id for c in all_cities}

        # Рейсы
        existing_flights = (
            (await session.execute(select(Flight.flight_number))).scalars().all()
        )
        existing_numbers = set(existing_flights)

        base = datetime.now(timezone.utc).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        new_flights: list[Flight] = []

        for i, (orig, dest, airline, aircraft, dur, price) in enumerate(ROUTES):
            # Создаём 7 вылетов на ближайшие 7 дней
            for day_offset in range(7):
                dep = base + timedelta(days=day_offset, hours=i % 4)
                arr = dep + timedelta(minutes=dur)
                fn = f"{airline[:2].upper()}{1000 + i * 7 + day_offset}"
                if fn in existing_numbers:
                    continue
                new_flights.append(
                    Flight(
                        flight_number=fn,
                        airline=airline,
                        aircraft=aircraft,
                        origin_id=by_code[orig],
                        destination_id=by_code[dest],
                        departure_at=dep,
                        arrival_at=arr,
                        duration_minutes=dur,
                        base_price=price,
                        seats_total=180,
                        seats_available=180 - (day_offset * 15),
                        is_active=True,
                    )
                )
                existing_numbers.add(fn)

        session.add_all(new_flights)
        await session.commit()

    print(f"✓ Добавлено городов: {len(cities_added)}")
    print(f"✓ Добавлено рейсов: {len(new_flights)}")
    print(f"✓ Всего городов: {len(all_cities)}")
    print(f"✓ Всего рейсов: {len(existing_numbers)}")

    # Демо-пользователь
    demo_email = "demo@skyroutes.local"
    existing_user = await session.execute(select(User).where(User.email == demo_email))
    if not existing_user.scalar_one_or_none():
        session.add(
            User(
                email=demo_email,
                full_name="Демо Пользователь",
                password_hash=hash_password("demo1234"),
                is_admin=True,
            )
        )
        await session.commit()
        print(f"✓ Создан демо-пользователь: {demo_email} / demo1234")
    else:
        print(f"→ Демо-пользователь уже существует: {demo_email}")


if __name__ == "__main__":
    asyncio.run(seed())
