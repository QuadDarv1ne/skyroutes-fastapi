"""Pydantic-схемы для API."""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import CabinClass, BookingStatus


# ----- City -----
class CityRead(BaseModel):
    id: int
    code: str
    name: str
    country: str
    timezone: str = "Europe/Moscow"

    model_config = ConfigDict(from_attributes=True)


# ----- Flight -----
class FlightRead(BaseModel):
    id: int
    flight_number: str
    airline: str
    aircraft: str
    origin: CityRead = Field(
        serialization_alias="origin", validation_alias="origin_city"
    )
    destination: CityRead = Field(
        serialization_alias="destination", validation_alias="destination_city"
    )
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    base_price: float
    seats_available: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FlightSearchParams(BaseModel):
    """Параметры поиска рейсов."""

    origin_code: Optional[str] = Field(None, description="IATA-код города вылета")
    destination_code: Optional[str] = Field(None, description="IATA-код города прилёта")
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    max_price: Optional[float] = None
    min_seats: int = Field(1, ge=1)
    airline: Optional[str] = None


class FlightCreate(BaseModel):
    """Создание рейса (для админ-API)."""

    flight_number: str = Field(..., min_length=3, max_length=10)
    airline: str = Field(..., min_length=2, max_length=128)
    aircraft: str = Field("Airbus A320", max_length=64)
    origin_id: int
    destination_id: int
    departure_at: datetime
    arrival_at: datetime
    base_price: float = Field(..., gt=0)
    seats_total: int = Field(180, ge=1, le=600)
    is_active: bool = True


class FlightUpdate(BaseModel):
    """Частичное обновление рейса (для админ-API)."""

    airline: Optional[str] = Field(None, min_length=2, max_length=128)
    aircraft: Optional[str] = Field(None, max_length=64)
    base_price: Optional[float] = Field(None, gt=0)
    seats_total: Optional[int] = Field(None, ge=1, le=600)
    is_active: Optional[bool] = None
    departure_at: Optional[datetime] = None
    arrival_at: Optional[datetime] = None


class CityCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=1, max_length=128)
    country: str = Field(..., min_length=1, max_length=128)
    timezone: str = Field("Europe/Moscow", max_length=64)


# ----- Statistics -----
class StatsResponse(BaseModel):
    """Сводная статистика для админ-панели."""

    flights_total: int
    flights_active: int
    bookings_total: int
    bookings_pending: int
    bookings_confirmed: int
    bookings_cancelled: int
    revenue_total: float
    revenue_pending: float
    passengers_total: int
    users_total: int
    cities_total: int


class PopularRoute(BaseModel):
    origin_code: str
    origin_name: str
    destination_code: str
    destination_name: str
    bookings_count: int
    revenue: float


class StatsResponseExtended(BaseModel):
    """Расширенная статистика с популярными направлениями."""

    basic: StatsResponse
    popular_routes: list[PopularRoute]
    top_airlines: list[dict]


# ----- Passenger -----
class PassengerCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date
    passport_number: str = Field(..., min_length=6, max_length=32)
    cabin_class: CabinClass = CabinClass.ECONOMY


class PassengerRead(PassengerCreate):
    id: int
    booking_id: int

    model_config = ConfigDict(from_attributes=True)


# ----- Booking -----
class BookingCreate(BaseModel):
    flight_id: int
    contact_email: EmailStr
    contact_phone: str = Field(..., min_length=6, max_length=32)
    passengers: list[PassengerCreate] = Field(..., min_length=1, max_length=9)


class BookingRead(BaseModel):
    id: int
    code: str
    flight_id: int
    user_id: Optional[int] = None
    contact_email: str
    contact_phone: str
    total_price: float
    status: BookingStatus
    created_at: datetime
    passengers: list[PassengerRead]

    model_config = ConfigDict(from_attributes=True)


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


# ----- Auth / User -----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
