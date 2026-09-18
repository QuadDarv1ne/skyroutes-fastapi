"""Админ-API: управление рейсами, городами и статистика.

Все эндпоинты требуют JWT-токен пользователя с флагом is_admin=True.
Все админ-действия логируются в таблицу audit_logs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_city,
    create_flight,
    delete_flight,
    get_flight,
    get_stats,
    get_popular_routes,
    get_top_airlines,
    get_bookings_by_day,
    get_avg_prices_by_route,
    get_bookings_status_breakdown,
    get_audit_logs,
    log_admin_action,
    update_flight,
)
from app.database import get_db
from app.models import User
from app.schemas import (
    CityCreate,
    CityRead,
    FlightCreate,
    FlightRead,
    FlightUpdate,
)
from app.security import require_admin


router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _log(request: Request, db, user, action, entity_type=None, entity_id=None, details=None):
    """Хелпер: записывает действие в аудит-лог."""
    ip = request.client.host if request.client else None
    await log_admin_action(
        db,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip,
    )


# ----- Управление рейсами -----
@router.post(
    "/flights",
    response_model=FlightRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать рейс (только админ)",
)
async def admin_create_flight(
    payload: FlightCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> FlightRead:
    if payload.arrival_at <= payload.departure_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="arrival_at must be after departure_at",
        )
    if payload.origin_id == payload.destination_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="origin and destination must differ",
        )
    flight = await create_flight(db, payload)
    await _log(request, db, user, "create_flight",
               entity_type="flight", entity_id=flight.id,
               details=f"Flight {flight.flight_number}")
    await db.commit()
    # Перечитываем с предзагрузкой связей origin_city/destination_city
    refreshed = await get_flight(db, flight.id)
    return FlightRead.model_validate(refreshed)


@router.patch(
    "/flights/{flight_id}",
    response_model=FlightRead,
    summary="Обновить рейс (только админ)",
)
async def admin_update_flight(
    flight_id: int,
    payload: FlightUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> FlightRead:
    flight = await update_flight(db, flight_id, payload)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    await _log(request, db, user, "update_flight",
               entity_type="flight", entity_id=flight.id,
               details=f"Updated fields: {list(payload.model_dump(exclude_unset=True).keys())}")
    await db.commit()
    refreshed = await get_flight(db, flight.id)
    return FlightRead.model_validate(refreshed)


@router.delete(
    "/flights/{flight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Деактивировать рейс (только админ)",
)
async def admin_delete_flight(
    flight_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    ok = await delete_flight(db, flight_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Flight not found")
    await _log(request, db, user, "delete_flight",
               entity_type="flight", entity_id=flight_id,
               details="Flight deactivated")
    await db.commit()


# ----- Управление городами -----
@router.post(
    "/cities",
    response_model=CityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать город (только админ)",
)
async def admin_create_city(
    payload: CityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> CityRead:
    city = await create_city(db, payload)
    await _log(request, db, user, "create_city",
               entity_type="city", entity_id=city.id,
               details=f"City {city.code} ({city.name})")
    await db.commit()
    return CityRead.model_validate(city)


# ----- Аудит-лог -----
@router.get("/audit", summary="Последние действия администраторов")
async def admin_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[dict]:
    """Возвращает последние записи из аудит-лога."""
    logs = await get_audit_logs(db, limit=limit)
    return [
        {
            "id": log.id,
            "user_email": log.user_email,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ----- Статистика -----
@router.get("/stats", summary="Сводная статистика (только админ)")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Базовые счётчики: рейсы, бронирования, выручка, пользователи."""
    return await get_stats(db)


@router.get("/stats/extended", summary="Расширенная статистика с топами (только админ)")
async def admin_stats_extended(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Базовые счётчики + топ направлений + топ авиакомпаний."""
    basic = await get_stats(db)
    popular = await get_popular_routes(db, limit=5)
    airlines = await get_top_airlines(db, limit=5)
    return {
        "basic": basic,
        "popular_routes": popular,
        "top_airlines": airlines,
    }


# ----- Аналитика для графиков -----
@router.get("/charts/bookings-by-day", summary="Бронирования по дням (для графика)")
async def admin_bookings_by_day(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[dict]:
    """Количество бронирований и выручка по дням за последние N дней."""
    return await get_bookings_by_day(db, days=days)


@router.get("/charts/avg-prices", summary="Средние цены по направлениям")
async def admin_avg_prices(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[dict]:
    """Средние/мин/макс цены по топ-N направлениям."""
    return await get_avg_prices_by_route(db, limit=limit)


@router.get("/charts/status-breakdown", summary="Распределение бронирований по статусам")
async def admin_status_breakdown(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Распределение по статусам: pending, confirmed, cancelled."""
    return await get_bookings_status_breakdown(db)
