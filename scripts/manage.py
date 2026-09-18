"""CLI-утилита для управления SkyRoutes.

Команды:
    python scripts/manage.py create-admin --email admin@x.com --password secret --name "Admin"
    python scripts/manage.py create-user  --email user@x.com --password secret --name "User"
    python scripts/manage.py create-flight --number SU9999 --airline "Аэрофлот" --origin 1 --dest 3 --dep "2026-10-01T10:00" --arr "2026-10-01T13:00" --price 25000 --seats 200
    python scripts/manage.py stats
    python scripts/manage.py reset-db
    python scripts/manage.py export-openapi --output openapi.json

Запуск:
    cd /path/to/skyroutes
    python scripts/manage.py <command> [args]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Активируем правильное окружение
os.environ.setdefault("TRAVEL_DATABASE_URL", "sqlite+aiosqlite:///./travel.db")
os.environ.setdefault("TRAVEL_DEBUG", "False")


async def cmd_create_admin(args):
    """Создать пользователя-администратора."""
    from app.crud import create_user, get_user_by_email
    from app.database import async_session_factory, init_db

    await init_db()
    async with async_session_factory() as db:
        existing = await get_user_by_email(db, args.email)
        if existing:
            print(f"❌ Пользователь {args.email} уже существует")
            return 1
        user = await create_user(db, args.email, args.password, args.name, is_admin=True)
        await db.commit()
        print(f"✅ Создан администратор: {user.email} (id={user.id})")
    return 0


async def cmd_create_user(args):
    """Создать обычного пользователя."""
    from app.crud import create_user, get_user_by_email
    from app.database import async_session_factory, init_db

    await init_db()
    async with async_session_factory() as db:
        existing = await get_user_by_email(db, args.email)
        if existing:
            print(f"❌ Пользователь {args.email} уже существует")
            return 1
        user = await create_user(db, args.email, args.password, args.name, is_admin=False)
        await db.commit()
        print(f"✅ Создан пользователь: {user.email} (id={user.id})")
    return 0


async def cmd_create_flight(args):
    """Создать новый рейс."""
    from app.crud import create_flight
    from app.database import async_session_factory, init_db
    from app.schemas import FlightCreate

    await init_db()
    async with async_session_factory() as db:
        try:
            payload = FlightCreate(
                flight_number=args.number,
                airline=args.airline,
                aircraft=args.aircraft or "Airbus A320",
                origin_id=args.origin,
                destination_id=args.dest,
                departure_at=datetime.fromisoformat(args.dep),
                arrival_at=datetime.fromisoformat(args.arr),
                base_price=args.price,
                seats_total=args.seats,
            )
        except Exception as e:
            print(f"❌ Ошибка валидации: {e}")
            return 1

        flight = await create_flight(db, payload)
        await db.commit()
        print(f"✅ Создан рейс: {flight.flight_number} (id={flight.id})")
    return 0


async def cmd_stats(args):
    """Показать сводную статистику."""
    from app.crud import get_stats, get_popular_routes, get_top_airlines
    from app.database import async_session_factory, init_db

    await init_db()
    async with async_session_factory() as db:
        stats = await get_stats(db)
        print("\n=== Сводная статистика SkyRoutes ===\n")
        print(f"  Рейсы:           {stats['flights_active']} активных из {stats['flights_total']}")
        print(f"  Бронирования:    {stats['bookings_total']} всего")
        print(f"    - pending:     {stats['bookings_pending']}")
        print(f"    - confirmed:   {stats['bookings_confirmed']}")
        print(f"    - cancelled:   {stats['bookings_cancelled']}")
        print(f"  Выручка:         {stats['revenue_total']:.2f} ₽")
        print(f"    - в ожидании:  {stats['revenue_pending']:.2f} ₽")
        print(f"  Пассажиры:       {stats['passengers_total']}")
        print(f"  Пользователи:    {stats['users_total']}")
        print(f"  Города:          {stats['cities_total']}")

        popular = await get_popular_routes(db, limit=5)
        if popular:
            print("\n=== Топ-5 популярных направлений ===\n")
            for i, r in enumerate(popular, 1):
                print(f"  {i}. {r['origin_code']} → {r['destination_code']}: "
                      f"{r['bookings_count']} броней, {r['revenue']:.0f} ₽")

        airlines = await get_top_airlines(db, limit=5)
        if airlines:
            print("\n=== Топ-5 авиакомпаний по выручке ===\n")
            for i, a in enumerate(airlines, 1):
                print(f"  {i}. {a['airline']}: {a['bookings_count']} броней, {a['revenue']:.0f} ₽")
    return 0


async def cmd_reset_db(args):
    """Удалить и пересоздать базу данных."""
    from app.database import engine
    from app.models import Base

    if not args.yes:
        confirm = input("⚠️  Это удалит все данные. Продолжить? [y/N] ")
        if confirm.lower() not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return 0

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных пересоздана. Выполните `python -m app.seed` для заполнения тестовыми данными.")
    return 0


def cmd_export_openapi(args):
    """Экспорт OpenAPI-спецификации в JSON-файл."""
    from app.main import app

    spec = app.openapi()
    output = args.output or "openapi.json"
    Path(output).write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ OpenAPI спецификация сохранена в {output} ({len(spec)} символов)")
    return 0


def cmd_list_routes(args):
    """Вывести список всех маршрутов API."""
    from app.main import app

    print(f"\n=== Маршруты SkyRoutes ({len(app.routes)}) ===\n")
    for route in app.routes:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "?")
        name = getattr(route, "name", "")
        if methods:
            methods_str = ", ".join(sorted(methods - {"HEAD", "OPTIONS"}))
            print(f"  {methods_str:20} {path:50} {name}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="CLI-утилита для управления SkyRoutes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/manage.py create-admin --email admin@x.com --password secret --name "Admin"
  python scripts/manage.py stats
  python scripts/manage.py export-openapi --output openapi.json
  python scripts/manage.py list-routes
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды", required=True)

    # create-admin
    p_admin = subparsers.add_parser("create-admin", help="Создать администратора")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--password", required=True)
    p_admin.add_argument("--name", required=True)

    # create-user
    p_user = subparsers.add_parser("create-user", help="Создать обычного пользователя")
    p_user.add_argument("--email", required=True)
    p_user.add_argument("--password", required=True)
    p_user.add_argument("--name", required=True)

    # create-flight
    p_flight = subparsers.add_parser("create-flight", help="Создать новый рейс")
    p_flight.add_argument("--number", required=True, help="Номер рейса (напр. SU9999)")
    p_flight.add_argument("--airline", required=True, help="Авиакомпания")
    p_flight.add_argument("--aircraft", default=None, help="Тип судна (по умолч. Airbus A320)")
    p_flight.add_argument("--origin", type=int, required=True, help="ID города вылета")
    p_flight.add_argument("--dest", type=int, required=True, help="ID города прилёта")
    p_flight.add_argument("--dep", required=True, help="Время вылета ISO (2026-10-01T10:00)")
    p_flight.add_argument("--arr", required=True, help="Время прилёта ISO")
    p_flight.add_argument("--price", type=float, required=True, help="Базовая цена")
    p_flight.add_argument("--seats", type=int, default=180, help="Кол-во мест (по умолч. 180)")

    # stats
    subparsers.add_parser("stats", help="Показать сводную статистику")

    # reset-db
    p_reset = subparsers.add_parser("reset-db", help="Удалить и пересоздать базу данных")
    p_reset.add_argument("--yes", "-y", action="store_true", help="Не спрашивать подтверждение")

    # export-openapi
    p_export = subparsers.add_parser("export-openapi", help="Экспорт OpenAPI спецификации в JSON")
    p_export.add_argument("--output", "-o", default=None, help="Имя файла (по умолч. openapi.json)")

    # list-routes
    subparsers.add_parser("list-routes", help="Список всех маршрутов API")

    args = parser.parse_args()

    # Синхронные команды
    if args.command == "export-openapi":
        sys.exit(cmd_export_openapi(args))
    if args.command == "list-routes":
        sys.exit(cmd_list_routes(args))

    # Асинхронные команды
    handlers = {
        "create-admin": cmd_create_admin,
        "create-user": cmd_create_user,
        "create-flight": cmd_create_flight,
        "stats": cmd_stats,
        "reset-db": cmd_reset_db,
    }
    handler = handlers[args.command]
    sys.exit(asyncio.run(handler(args)))


if __name__ == "__main__":
    main()
