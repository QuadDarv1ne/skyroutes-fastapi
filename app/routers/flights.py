"""API рейсов: список, поиск, детали + пагинация, сортировка, X-Total-Count."""
from __future__ import annotations

from datetime import date
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from slowapi import _rate_limit_exceeded_handler  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud import (
    count_flights_filtered,
    get_flights,
    get_flight,
    add_search_history,
)
from app.database import get_db
from app.models import User
from app.schemas import FlightRead
from app.security import get_current_user


router = APIRouter(prefix="/api/flights", tags=["flights"])

SortField = Literal["departure_at", "base_price", "duration_minutes"]
SortOrder = Literal["asc", "desc"]


@router.get("", response_model=list[FlightRead], summary="Поиск рейсов")
async def list_flights(
    request: Request,
    response: Response,
    origin: Optional[str] = Query(None, description="IATA-код вылета, напр. MOW"),
    destination: Optional[str] = Query(None, description="IATA-код прилёта, напр. LED"),
    date_from: Optional[date] = Query(None, description="Дата вылета с (включительно)"),
    date_to: Optional[date] = Query(None, description="Дата вылета по (включительно)"),
    max_price: Optional[float] = Query(None, ge=0),
    airline: Optional[str] = None,
    min_seats: int = Query(1, ge=1),
    sort_by: SortField = Query("departure_at", description="Поле сортировки"),
    sort_order: SortOrder = Query("asc", description="Направление сортировки"),
    limit: int = Query(settings.page_size, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> list[FlightRead]:
    flights = await get_flights(
        db,
        origin_code=origin,
        destination_code=destination,
        date_from=date_from,
        date_to=date_to,
        max_price=max_price,
        min_seats=min_seats,
        airline=airline,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Сохраняем в историю поиска
    try:
        total_count = await count_flights_filtered(
            db,
            origin_code=origin,
            destination_code=destination,
            date_from=date_from,
            date_to=date_to,
            max_price=max_price,
            min_seats=min_seats,
            airline=airline,
        )
        # Заголовок с общим числом (для пагинации на клиенте)
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Page-Size"] = str(limit)
        response.headers["X-Page-Offset"] = str(offset)

        # История поиска сохраняется только если указан хотя бы один фильтр
        if origin or destination or date_from or max_price:
            await add_search_history(
                db,
                user_id=user.id if user else None,
                origin_code=origin,
                destination_code=destination,
                date_from=date_from,
                date_to=date_to,
                max_price=max_price,
                results_count=total_count,
            )
            await db.commit()
    except Exception:  # noqa: BLE001
        # История поиска не должна ломать основной запрос
        pass

    return [FlightRead.model_validate(f) for f in flights]


@router.get("/{flight_id}", response_model=FlightRead, summary="Детали рейса")
async def flight_detail(flight_id: int, db: AsyncSession = Depends(get_db)) -> FlightRead:
    flight = await get_flight(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return FlightRead.model_validate(flight)
