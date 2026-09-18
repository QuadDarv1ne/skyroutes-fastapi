"""API бронирований: создание, просмотр, изменение статуса, мои бронирования."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_booking,
    get_booking_by_code,
    get_bookings_by_email,
    get_user_bookings,
    update_booking_status,
)
from app.database import get_db
from app.models import BookingStatus, User
from app.schemas import BookingCreate, BookingRead, BookingStatusUpdate
from app.security import get_current_user, require_user


router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingRead, status_code=201, summary="Создать бронирование")
async def book_flight(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> BookingRead:
    booking = await create_booking(db, payload, user_id=user.id if user else None)
    if booking is None:
        raise HTTPException(
            status_code=409,
            detail="Flight not found or not enough available seats",
        )
    refreshed = await get_booking_by_code(db, booking.code)
    return BookingRead.model_validate(refreshed)


@router.get("/{code}", response_model=BookingRead, summary="Найти бронирование по PNR")
async def get_booking(code: str, db: AsyncSession = Depends(get_db)) -> BookingRead:
    booking = await get_booking_by_code(db, code)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingRead.model_validate(booking)


@router.patch("/{code}", response_model=BookingRead, summary="Изменить статус бронирования")
async def patch_booking_status(
    code: str, payload: BookingStatusUpdate, db: AsyncSession = Depends(get_db)
) -> BookingRead:
    booking = await update_booking_status(db, code, payload.status)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingRead.model_validate(booking)


@router.get("", response_model=list[BookingRead], summary="Мои бронирования")
async def my_bookings(
    email: str | None = Query(None, description="Email для поиска без авторизации"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> list[BookingRead]:
    if email:
        bookings = await get_bookings_by_email(db, email)
    else:
        bookings = await get_user_bookings(db, user.id)
    return [BookingRead.model_validate(b) for b in bookings]
