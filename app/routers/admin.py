"""Админ-API: управление рейсами, городами и статистика.

Все эндпоинты требуют JWT-токен пользователя с флагом is_admin=True.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_city,
    create_flight,
    delete_flight,
    get_flight,
    get_stats,
    get_popular_routes,
    get_top_airlines,
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


# ----- Управление рейсами -----
@router.post(
    "/flights",
    response_model=FlightRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать рейс (только админ)",
)
async def admin_create_flight(
    payload: FlightCreate,
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> FlightRead:
    flight = await update_flight(db, flight_id, payload)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    await db.commit()
    # Перечитываем с relations
    refreshed = await get_flight(db, flight.id)
    return FlightRead.model_validate(refreshed)


@router.delete(
    "/flights/{flight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Деактивировать рейс (только админ)",
)
async def admin_delete_flight(
    flight_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    ok = await delete_flight(db, flight_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Flight not found")
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> CityRead:
    city = await create_city(db, payload)
    await db.commit()
    return CityRead.model_validate(city)


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
