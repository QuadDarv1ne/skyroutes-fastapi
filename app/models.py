"""ORM-модели: рейсы, города, бронирования, пассажиры, пользователи, избранное, история поиска."""

from __future__ import annotations

from datetime import datetime, date, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Enum,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CabinClass(str, PyEnum):
    """Класс обслуживания."""

    ECONOMY = "economy"
    PREMIUM = "premium"
    BUSINESS = "business"
    FIRST = "first"


class BookingStatus(str, PyEnum):
    """Статус бронирования."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class City(Base):
    """Город с аэропортом."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(3), unique=True, index=True
    )  # IATA: SVO, DME, LED...
    name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")

    departures: Mapped[list["Flight"]] = relationship(
        back_populates="origin_city", foreign_keys="Flight.origin_id"
    )
    arrivals: Mapped[list["Flight"]] = relationship(
        back_populates="destination_city", foreign_keys="Flight.destination_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<City {self.code} {self.name}>"


class Flight(Base):
    """Рейс между городами."""

    __tablename__ = "flights"
    __table_args__ = (
        # Составной индекс для поиска по маршруту + дате
        Index("ix_flights_route_date", "origin_id", "destination_id", "departure_at"),
        # Индекс для фильтра по цене
        Index("ix_flights_price", "base_price"),
        # Индекс для фильтра активных рейсов с датой
        Index("ix_flights_active_departure", "is_active", "departure_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    airline: Mapped[str] = mapped_column(String(128))
    aircraft: Mapped[str] = mapped_column(String(64), default="Airbus A320")

    origin_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))
    destination_id: Mapped[int] = mapped_column(ForeignKey("cities.id"))

    departure_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    arrival_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(Integer)

    base_price: Mapped[float] = mapped_column(Float)
    seats_total: Mapped[int] = mapped_column(Integer, default=180)
    seats_available: Mapped[int] = mapped_column(Integer, default=180)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    origin_city: Mapped["City"] = relationship(
        back_populates="departures", foreign_keys=[origin_id]
    )
    destination_city: Mapped["City"] = relationship(
        back_populates="arrivals", foreign_keys=[destination_id]
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="flight")
    favorited_by: Mapped[list["Favorite"]] = relationship(
        back_populates="flight", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Flight {self.flight_number}>"


class User(Base):
    """Зарегистрированный пользователь (для JWT-аутентификации)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    search_history: Mapped[list["SearchHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"


class Passenger(Base):
    """Пассажир бронирования."""

    __tablename__ = "passengers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE")
    )
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64))
    birth_date: Mapped[date] = mapped_column(Date)
    passport_number: Mapped[str] = mapped_column(String(32))
    cabin_class: Mapped[CabinClass] = mapped_column(
        Enum(CabinClass), default=CabinClass.ECONOMY
    )

    booking: Mapped["Booking"] = relationship(back_populates="passengers")


class Booking(Base):
    """Бронирование рейса."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_user_created", "user_id", "created_at"),
        Index("ix_bookings_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)  # PNR
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    contact_email: Mapped[str] = mapped_column(String(128), index=True)
    contact_phone: Mapped[str] = mapped_column(String(32))

    total_price: Mapped[float] = mapped_column(Float)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    flight: Mapped["Flight"] = relationship(back_populates="bookings")
    user: Mapped["User | None"] = relationship(back_populates="bookings")
    passengers: Mapped[list["Passenger"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Booking {self.code}>"


class Favorite(Base):
    """Избранный рейс пользователя."""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "flight_id", name="uq_user_flight"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="favorites")
    flight: Mapped["Flight"] = relationship(back_populates="favorited_by")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Favorite user={self.user_id} flight={self.flight_id}>"


class SearchHistory(Base):
    """История поисковых запросов пользователя (для персонализации)."""

    __tablename__ = "search_history"
    __table_args__ = (Index("ix_search_history_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    origin_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    destination_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User | None"] = relationship(back_populates="search_history")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SearchHistory {self.origin_code}->{self.destination_code}>"


class PasswordResetToken(Base):
    """Токен для сброса пароля (отправляется на email пользователя)."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_reset_tokens_user", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PasswordResetToken user={self.user_id} used={self.used}>"


class AuditLog(Base):
    """Аудит-лог действий администраторов."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
        Index("ix_audit_action", "action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_email: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} by {self.user_email}>"
