"""CRUD-операции с БД."""

from __future__ import annotations

import secrets
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models import (
    City,
    Flight,
    Booking,
    Passenger,
    User,
    CabinClass,
    BookingStatus,
    Favorite,
    SearchHistory,
    PasswordResetToken,
    AuditLog,
)
from app.schemas import BookingCreate
from app.security import hash_password


# ----- Cities -----
async def get_cities(db: AsyncSession) -> list[City]:
    result = await db.execute(select(City).order_by(City.name))
    return list(result.scalars().all())


async def get_city_by_code(db: AsyncSession, code: str) -> Optional[City]:
    result = await db.execute(select(City).where(City.code == code.upper()))
    return result.scalar_one_or_none()


# ----- Flights -----
async def get_flights(
    db: AsyncSession,
    *,
    origin_code: Optional[str] = None,
    destination_code: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    max_price: Optional[float] = None,
    min_seats: int = 1,
    airline: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "departure_at",
    sort_order: str = "asc",
) -> list[Flight]:
    """Поиск рейсов с фильтрами. Возвращает список с предзагруженными городами."""
    stmt = (
        select(Flight)
        .options(
            selectinload(Flight.origin_city),
            selectinload(Flight.destination_city),
        )
        .where(Flight.is_active.is_(True))
    )

    if origin_code:
        OriginCity = aliased(City)
        stmt = stmt.join(OriginCity, OriginCity.id == Flight.origin_id).where(
            OriginCity.code == origin_code.upper()
        )
    if destination_code:
        DestCity = aliased(City)
        stmt = stmt.join(
            DestCity,
            and_(
                DestCity.id == Flight.destination_id,
                DestCity.code == destination_code.upper(),
            ),
        )
    if date_from:
        stmt = stmt.where(
            Flight.departure_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        next_day = date_to + timedelta(days=1)
        stmt = stmt.where(
            Flight.departure_at < datetime.combine(next_day, datetime.min.time())
        )
    if max_price is not None:
        stmt = stmt.where(Flight.base_price <= max_price)
    if min_seats:
        stmt = stmt.where(Flight.seats_available >= min_seats)
    if airline:
        stmt = stmt.where(Flight.airline.ilike(f"%{airline}%"))

    # Сортировка
    sort_columns = {
        "departure_at": Flight.departure_at,
        "base_price": Flight.base_price,
        "duration_minutes": Flight.duration_minutes,
    }
    sort_col = sort_columns.get(sort_by, Flight.departure_at)
    if sort_order == "desc":
        sort_col = sort_col.desc()
    stmt = stmt.order_by(sort_col).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_flight(db: AsyncSession, flight_id: int) -> Optional[Flight]:
    stmt = (
        select(Flight)
        .options(
            selectinload(Flight.origin_city),
            selectinload(Flight.destination_city),
        )
        .where(Flight.id == flight_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ----- Bookings -----
CABIN_MULTIPLIER = {
    CabinClass.ECONOMY: 1.0,
    CabinClass.PREMIUM: 1.4,
    CabinClass.BUSINESS: 2.5,
    CabinClass.FIRST: 4.0,
}


def _generate_pnr() -> str:
    """6-символьный PNR (без неоднозначных символов)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


async def create_booking(
    db: AsyncSession, payload: BookingCreate, user_id: Optional[int] = None
) -> Optional[Booking]:
    """Создаёт бронирование, уменьшая кол-во доступных мест на рейсе."""
    flight = await get_flight(db, payload.flight_id)
    if not flight:
        return None

    if flight.seats_available < len(payload.passengers):
        return None

    total_price = sum(
        flight.base_price * CABIN_MULTIPLIER[p.cabin_class] for p in payload.passengers
    )

    booking = Booking(
        code=_generate_pnr(),
        flight_id=flight.id,
        user_id=user_id,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        total_price=round(total_price, 2),
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    await db.flush()  # чтобы получить booking.id

    for p in payload.passengers:
        db.add(Passenger(booking_id=booking.id, **p.model_dump()))

    flight.seats_available -= len(payload.passengers)
    await db.flush()
    return booking


async def get_booking_by_code(db: AsyncSession, code: str) -> Optional[Booking]:
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.passengers),
            selectinload(Booking.flight).selectinload(Flight.origin_city),
            selectinload(Booking.flight).selectinload(Flight.destination_city),
        )
        .where(Booking.code == code.upper())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_bookings_by_email(db: AsyncSession, email: str) -> list[Booking]:
    """Поиск бронирований по контактному email (для страницы «Мои бронирования»)."""
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.passengers),
            selectinload(Booking.flight).selectinload(Flight.origin_city),
            selectinload(Booking.flight).selectinload(Flight.destination_city),
        )
        .where(Booking.contact_email == email.lower())
        .order_by(Booking.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_bookings(db: AsyncSession, user_id: int) -> list[Booking]:
    """Все бронирования залогиненного пользователя."""
    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.passengers),
            selectinload(Booking.flight).selectinload(Flight.origin_city),
            selectinload(Booking.flight).selectinload(Flight.destination_city),
        )
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_booking_status(
    db: AsyncSession, code: str, status: BookingStatus
) -> Optional[Booking]:
    booking = await get_booking_by_code(db, code)
    if not booking:
        return None
    # При отмене возвращаем места в рейс
    if status == BookingStatus.CANCELLED and booking.status != BookingStatus.CANCELLED:
        flight = await get_flight(db, booking.flight_id)
        if flight:
            flight.seats_available += len(booking.passengers)
    booking.status = status
    await db.flush()
    return booking


async def count_flights(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Flight.id)))
    return int(result.scalar_one())


async def count_flights_filtered(
    db: AsyncSession,
    *,
    origin_code: Optional[str] = None,
    destination_code: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    max_price: Optional[float] = None,
    min_seats: int = 1,
    airline: Optional[str] = None,
) -> int:
    """Считает общее число рейсов по тем же фильтрам (для пагинации)."""
    stmt = select(func.count(Flight.id)).where(Flight.is_active.is_(True))

    if origin_code:
        OriginCity = aliased(City)
        stmt = stmt.join(OriginCity, OriginCity.id == Flight.origin_id).where(
            OriginCity.code == origin_code.upper()
        )
    if destination_code:
        DestCity = aliased(City)
        stmt = stmt.join(
            DestCity,
            and_(
                DestCity.id == Flight.destination_id,
                DestCity.code == destination_code.upper(),
            ),
        )
    if date_from:
        stmt = stmt.where(
            Flight.departure_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        next_day = date_to + timedelta(days=1)
        stmt = stmt.where(
            Flight.departure_at < datetime.combine(next_day, datetime.min.time())
        )
    if max_price is not None:
        stmt = stmt.where(Flight.base_price <= max_price)
    if min_seats:
        stmt = stmt.where(Flight.seats_available >= min_seats)
    if airline:
        stmt = stmt.where(Flight.airline.ilike(f"%{airline}%"))

    result = await db.execute(stmt)
    return int(result.scalar_one())


# ----- Users -----
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, email: str, password: str, full_name: str, is_admin: bool = False
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()
    return user


# ----- Admin: Flights CRUD -----
async def create_flight(db: AsyncSession, payload) -> Flight:
    """Создание нового рейса (для админов)."""
    flight = Flight(
        flight_number=payload.flight_number,
        airline=payload.airline,
        aircraft=payload.aircraft,
        origin_id=payload.origin_id,
        destination_id=payload.destination_id,
        departure_at=payload.departure_at,
        arrival_at=payload.arrival_at,
        duration_minutes=int(
            (payload.arrival_at - payload.departure_at).total_seconds() // 60
        ),
        base_price=payload.base_price,
        seats_total=payload.seats_total,
        seats_available=payload.seats_total,
        is_active=payload.is_active,
    )
    db.add(flight)
    await db.flush()
    return flight


async def update_flight(db: AsyncSession, flight_id: int, payload) -> Optional[Flight]:
    """Частичное обновление рейса. Если меняется seats_total — корректируем seats_available."""
    flight = await get_flight(db, flight_id)
    if not flight:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Если меняется seats_total — пересчитываем available
    if "seats_total" in update_data:
        diff = update_data["seats_total"] - flight.seats_total
        flight.seats_available = max(0, flight.seats_available + diff)

    # Если меняются даты — пересчитываем длительность
    new_dep = update_data.get("departure_at", flight.departure_at)
    new_arr = update_data.get("arrival_at", flight.arrival_at)
    if new_arr > new_dep:
        flight.duration_minutes = int((new_arr - new_dep).total_seconds() // 60)

    for key, value in update_data.items():
        if key not in ("seats_total", "departure_at", "arrival_at"):
            setattr(flight, key, value)

    await db.flush()
    return flight


async def delete_flight(db: AsyncSession, flight_id: int) -> bool:
    """Мягкое удаление: помечаем рейс как неактивный."""
    flight = await get_flight(db, flight_id)
    if not flight:
        return False
    flight.is_active = False
    await db.flush()
    return True


# ----- Admin: Statistics -----
async def get_stats(db: AsyncSession) -> dict:
    """Сводная статистика по приложению."""
    from app.models import BookingStatus

    # Flights
    flights_total = (await db.execute(select(func.count(Flight.id)))).scalar_one()
    flights_active = (
        await db.execute(
            select(func.count(Flight.id)).where(Flight.is_active.is_(True))
        )
    ).scalar_one()

    # Bookings
    bookings_total = (await db.execute(select(func.count(Booking.id)))).scalar_one()
    bookings_pending = (
        await db.execute(
            select(func.count(Booking.id)).where(
                Booking.status == BookingStatus.PENDING
            )
        )
    ).scalar_one()
    bookings_confirmed = (
        await db.execute(
            select(func.count(Booking.id)).where(
                Booking.status == BookingStatus.CONFIRMED
            )
        )
    ).scalar_one()
    bookings_cancelled = (
        await db.execute(
            select(func.count(Booking.id)).where(
                Booking.status == BookingStatus.CANCELLED
            )
        )
    ).scalar_one()

    # Revenue
    revenue_total = (
        await db.execute(
            select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
                Booking.status != BookingStatus.CANCELLED
            )
        )
    ).scalar_one()
    revenue_pending = (
        await db.execute(
            select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
                Booking.status == BookingStatus.PENDING
            )
        )
    ).scalar_one()

    # Passengers
    passengers_total = (await db.execute(select(func.count(Passenger.id)))).scalar_one()

    # Users
    users_total = (await db.execute(select(func.count(User.id)))).scalar_one()

    # Cities
    cities_total = (await db.execute(select(func.count(City.id)))).scalar_one()

    return {
        "flights_total": int(flights_total),
        "flights_active": int(flights_active),
        "bookings_total": int(bookings_total),
        "bookings_pending": int(bookings_pending),
        "bookings_confirmed": int(bookings_confirmed),
        "bookings_cancelled": int(bookings_cancelled),
        "revenue_total": float(revenue_total),
        "revenue_pending": float(revenue_pending),
        "passengers_total": int(passengers_total),
        "users_total": int(users_total),
        "cities_total": int(cities_total),
    }


async def get_popular_routes(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Топ направлений по числу бронирований."""
    OriginCity = aliased(City)
    DestCity = aliased(City)

    stmt = (
        select(
            OriginCity.code.label("origin_code"),
            OriginCity.name.label("origin_name"),
            DestCity.code.label("destination_code"),
            DestCity.name.label("destination_name"),
            func.count(Booking.id).label("bookings_count"),
            func.coalesce(func.sum(Booking.total_price), 0.0).label("revenue"),
        )
        .select_from(Booking)
        .join(Flight, Flight.id == Booking.flight_id)
        .join(OriginCity, OriginCity.id == Flight.origin_id)
        .join(DestCity, DestCity.id == Flight.destination_id)
        .where(Booking.status != BookingStatus.CANCELLED)
        .group_by(
            OriginCity.code,
            OriginCity.name,
            DestCity.code,
            DestCity.name,
        )
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


async def get_top_airlines(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Топ авиакомпаний по выручке."""
    stmt = (
        select(
            Flight.airline.label("airline"),
            func.count(Booking.id).label("bookings_count"),
            func.coalesce(func.sum(Booking.total_price), 0.0).label("revenue"),
        )
        .select_from(Booking)
        .join(Flight, Flight.id == Booking.flight_id)
        .where(Booking.status != BookingStatus.CANCELLED)
        .group_by(Flight.airline)
        .order_by(func.sum(Booking.total_price).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


# ----- Cities CRUD -----
async def create_city(db: AsyncSession, payload) -> City:
    """Создание города (для админов)."""
    city = City(
        code=payload.code.upper(),
        name=payload.name,
        country=payload.country,
        timezone=payload.timezone,
    )
    db.add(city)
    await db.flush()
    return city


# ----- Favorites -----
async def add_favorite(
    db: AsyncSession, user_id: int, flight_id: int
) -> Favorite | None:
    """Добавляет рейс в избранное. Возвращает None если уже в избранном или рейс не найден."""
    # Проверяем, существует ли рейс
    flight = await get_flight(db, flight_id)
    if not flight:
        return None
    # Проверяем, нет ли уже в избранном
    existing = await db.execute(
        select(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.flight_id == flight_id)
        )
    )
    if existing.scalar_one_or_none():
        return None
    fav = Favorite(user_id=user_id, flight_id=flight_id)
    db.add(fav)
    await db.flush()
    return fav


async def remove_favorite(db: AsyncSession, user_id: int, flight_id: int) -> bool:
    """Удаляет рейс из избранного."""
    result = await db.execute(
        select(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.flight_id == flight_id)
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        return False
    await db.delete(fav)
    await db.flush()
    return True


async def get_user_favorites(db: AsyncSession, user_id: int) -> list[Flight]:
    """Возвращает список избранных рейсов пользователя (с предзагрузкой городов)."""
    stmt = (
        select(Flight)
        .join(Favorite, Favorite.flight_id == Flight.id)
        .where(Favorite.user_id == user_id)
        .options(
            selectinload(Flight.origin_city),
            selectinload(Flight.destination_city),
        )
        .order_by(Favorite.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def is_favorite(db: AsyncSession, user_id: int, flight_id: int) -> bool:
    """Проверяет, находится ли рейс в избранном у пользователя."""
    result = await db.execute(
        select(func.count(Favorite.id)).where(
            and_(Favorite.user_id == user_id, Favorite.flight_id == flight_id)
        )
    )
    return int(result.scalar_one()) > 0


# ----- Search History -----
async def add_search_history(
    db: AsyncSession,
    *,
    user_id: int | None,
    origin_code: str | None,
    destination_code: str | None,
    date_from: date | None,
    date_to: date | None,
    max_price: float | None,
    results_count: int,
) -> SearchHistory:
    """Сохраняет поисковый запрос в историю."""
    entry = SearchHistory(
        user_id=user_id,
        origin_code=origin_code.upper() if origin_code else None,
        destination_code=destination_code.upper() if destination_code else None,
        date_from=date_from,
        date_to=date_to,
        max_price=max_price,
        results_count=results_count,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_user_search_history(
    db: AsyncSession, user_id: int, limit: int = 10
) -> list[SearchHistory]:
    """Возвращает последние поисковые запросы пользователя."""
    stmt = (
        select(SearchHistory)
        .where(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ----- Analytics for charts -----
async def get_bookings_by_day(db: AsyncSession, days: int = 30) -> list[dict]:
    """Количество бронирований по дням (для графика)."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=days)

    stmt = (
        select(
            func.date(Booking.created_at).label("date"),
            func.count(Booking.id).label("count"),
            func.coalesce(func.sum(Booking.total_price), 0.0).label("revenue"),
        )
        .where(Booking.created_at >= since)
        .group_by(func.date(Booking.created_at))
        .order_by(func.date(Booking.created_at).asc())
    )
    result = await db.execute(stmt)
    return [
        {"date": str(row.date), "count": int(row.count), "revenue": float(row.revenue)}
        for row in result.all()
    ]


async def get_avg_prices_by_route(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Средние цены по направлениям (для графика)."""
    OriginCity = aliased(City)
    DestCity = aliased(City)

    stmt = (
        select(
            OriginCity.code.label("origin_code"),
            OriginCity.name.label("origin_name"),
            DestCity.code.label("destination_code"),
            DestCity.name.label("destination_name"),
            func.count(Flight.id).label("flights_count"),
            func.round(func.avg(Flight.base_price), 2).label("avg_price"),
            func.min(Flight.base_price).label("min_price"),
            func.max(Flight.base_price).label("max_price"),
        )
        .select_from(Flight)
        .join(OriginCity, OriginCity.id == Flight.origin_id)
        .join(DestCity, DestCity.id == Flight.destination_id)
        .where(Flight.is_active.is_(True))
        .group_by(
            OriginCity.code,
            OriginCity.name,
            DestCity.code,
            DestCity.name,
        )
        .order_by(func.count(Flight.id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


async def get_bookings_status_breakdown(db: AsyncSession) -> dict:
    """Распределение бронирований по статусам (для pie chart)."""
    stmt = select(
        Booking.status.label("status"),
        func.count(Booking.id).label("count"),
    ).group_by(Booking.status)
    result = await db.execute(stmt)
    return {
        row.status.value if hasattr(row.status, "value") else str(row.status): int(
            row.count
        )
        for row in result.all()
    }


# ----- Password reset -----
async def create_password_reset_token(db: AsyncSession, user: User) -> str:
    """Создаёт токен сброса пароля для пользователя (валиден 1 час)."""
    import secrets as _secrets
    from datetime import timedelta

    token = _secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
    )
    db.add(reset)
    await db.flush()
    return token


async def verify_password_reset_token(db: AsyncSession, token: str) -> User | None:
    """Проверяет токен и возвращает пользователя, либо None."""
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset = result.scalar_one_or_none()
    if not reset or reset.used:
        return None
    if reset.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None
    user = await get_user_by_id(db, reset.user_id)
    return user


async def use_password_reset_token(
    db: AsyncSession, token: str, new_password: str
) -> bool:
    """Использует токен и меняет пароль пользователя."""
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset = result.scalar_one_or_none()
    if not reset or reset.used:
        return False
    if reset.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return False
    user = await get_user_by_id(db, reset.user_id)
    if not user:
        return False
    user.password_hash = hash_password(new_password)
    reset.used = True
    await db.flush()
    return True


# ----- Audit log -----
async def log_admin_action(
    db: AsyncSession,
    *,
    user: User,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Записывает действие администратора в аудит-лог."""
    entry = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(db: AsyncSession, limit: int = 50) -> list[AuditLog]:
    """Возвращает последние записи аудита."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
