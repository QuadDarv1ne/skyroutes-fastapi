"""HTML-страницы (Jinja2): главная, поиск, бронирование, авторизация, профиль, избранное, история, about/contacts/admin."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.crud import (
    add_favorite,
    add_search_history,
    count_flights_filtered,
    create_booking,
    create_city,
    create_user,
    get_bookings_by_email,
    get_booking_by_code,
    get_cities,
    get_flight,
    get_flights,
    get_popular_routes,
    get_stats,
    get_top_airlines,
    get_user_bookings,
    get_user_by_email,
    get_user_favorites,
    get_user_search_history,
    get_bookings_by_day,
    get_avg_prices_by_route,
    get_bookings_status_breakdown,
    get_audit_logs,
    remove_favorite,
    update_booking_status,
)
from app.database import get_db
from app.models import BookingStatus, CabinClass, User
from app.security import (
    create_access_token,
    decode_token,
    get_current_user,
    verify_password,
)
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


# ---------- Хелперы ----------
async def get_user_from_request(request: Request, db: AsyncSession) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await get_user_by_email_or_id(db, int(user_id))
    return user


async def get_user_by_email_or_id(db: AsyncSession, user_id: int) -> User | None:
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def set_auth_cookie(response: RedirectResponse, token: str) -> RedirectResponse:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax",
    )
    return response


# ---------- Контекстный процессор ----------
async def base_context(request: Request, db: AsyncSession) -> dict:
    user = await get_user_from_request(request, db)
    return {"current_user": user, "settings": settings}


# ---------- Страницы ----------
@router.get("/", response_class=HTMLResponse, summary="Главная страница")
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    cities = await get_cities(db)
    ctx = await base_context(request, db)
    ctx.update({"request": request, "cities": cities})
    return templates.TemplateResponse(request, "index.html", ctx)


@router.get("/flights", response_class=HTMLResponse, summary="Страница поиска рейсов")
async def flights_page(
    request: Request,
    origin: str | None = None,
    destination: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    max_price: float | None = None,
    sort_by: str = "departure_at",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
):
    flights = await get_flights(
        db,
        origin_code=origin,
        destination_code=destination,
        date_from=date_from,
        date_to=date_to,
        max_price=max_price,
        limit=50,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cities = await get_cities(db)
    ctx = await base_context(request, db)
    ctx.update({
        "flights": flights,
        "cities": cities,
        "filters": {
            "origin": origin or "",
            "destination": destination or "",
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "max_price": max_price or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    })
    return templates.TemplateResponse(request, "flights.html", ctx)


@router.get("/booking/{flight_id}", response_class=HTMLResponse, summary="Форма бронирования")
async def booking_form(request: Request, flight_id: int, db: AsyncSession = Depends(get_db)):
    flight = await get_flight(db, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    ctx = await base_context(request, db)
    ctx.update({"flight": flight, "cabin_classes": list(CabinClass)})
    return templates.TemplateResponse(request, "booking.html", ctx)


@router.post("/booking/{flight_id}", summary="Создать бронирование из формы")
async def booking_submit(
    request: Request,
    flight_id: int,
    contact_email: str = Form(...),
    contact_phone: str = Form(...),
    passenger_first_name: list[str] = Form(...),
    passenger_last_name: list[str] = Form(...),
    passenger_birth_date: list[date] = Form(...),
    passenger_passport: list[str] = Form(...),
    passenger_cabin: list[CabinClass] = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas import BookingCreate, PassengerCreate

    user = await get_user_from_request(request, db)

    passengers = [
        PassengerCreate(
            first_name=fn,
            last_name=ln,
            birth_date=bd,
            passport_number=pp,
            cabin_class=cc,
        )
        for fn, ln, bd, pp, cc in zip(
            passenger_first_name,
            passenger_last_name,
            passenger_birth_date,
            passenger_passport,
            passenger_cabin,
        )
    ]
    payload = BookingCreate(
        flight_id=flight_id,
        contact_email=contact_email,
        contact_phone=contact_phone,
        passengers=passengers,
    )
    booking = await create_booking(db, payload, user_id=user.id if user else None)
    if booking is None:
        raise HTTPException(status_code=409, detail="Cannot create booking")
    return RedirectResponse(url=f"/booking/{booking.code}/view", status_code=303)


@router.get("/booking/{code}/view", response_class=HTMLResponse, summary="Просмотр бронирования")
async def booking_view(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    booking = await get_booking_by_code(db, code)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    ctx = await base_context(request, db)
    ctx.update({"booking": booking})
    return templates.TemplateResponse(request, "booking_view.html", ctx)


@router.get("/my-bookings", response_class=HTMLResponse, summary="Мои бронирования")
async def my_bookings_page(
    request: Request,
    email: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_request(request, db)
    if user:
        bookings = await get_user_bookings(db, user.id)
    elif email:
        bookings = await get_bookings_by_email(db, email)
    else:
        bookings = []
    ctx = await base_context(request, db)
    ctx.update({"bookings": bookings, "search_email": email or ""})
    return templates.TemplateResponse(request, "my_bookings.html", ctx)


# ---------- Аутентификация ----------
@router.get("/login", response_class=HTMLResponse, summary="Страница входа")
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    ctx = await base_context(request, db)
    return templates.TemplateResponse(request, "login.html", ctx)


@router.post("/login", summary="Вход через форму")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id, extra={"email": user.email, "admin": user.is_admin})
    response = RedirectResponse(url="/", status_code=303)
    return set_auth_cookie(response, token)


@router.get("/register", response_class=HTMLResponse, summary="Страница регистрации")
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    ctx = await base_context(request, db)
    return templates.TemplateResponse(request, "register.html", ctx)


@router.post("/register", summary="Регистрация через форму")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(..., min_length=8),
    full_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await create_user(db, email, password, full_name)
    await db.commit()
    token = create_access_token(user.id, extra={"email": user.email, "admin": user.is_admin})
    response = RedirectResponse(url="/", status_code=303)
    return set_auth_cookie(response, token)


@router.get("/logout", summary="Выход")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


# ---------- Информационные страницы ----------
@router.get("/about", response_class=HTMLResponse, summary="О проекте")
async def about_page(request: Request, db: AsyncSession = Depends(get_db)):
    ctx = await base_context(request, db)
    return templates.TemplateResponse(request, "about.html", ctx)


@router.get("/contacts", response_class=HTMLResponse, summary="Контакты")
async def contacts_page(request: Request, db: AsyncSession = Depends(get_db)):
    ctx = await base_context(request, db)
    return templates.TemplateResponse(request, "contacts.html", ctx)


# ---------- Админ-панель ----------
@router.get("/admin", response_class=HTMLResponse, summary="Админ-панель")
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    stats = await get_stats(db)
    popular = await get_popular_routes(db, limit=5)
    airlines = await get_top_airlines(db, limit=5)
    cities = await get_cities(db)

    # Данные для графиков
    bookings_by_day = await get_bookings_by_day(db, days=14)
    avg_prices = await get_avg_prices_by_route(db, limit=8)
    status_breakdown = await get_bookings_status_breakdown(db)

    ctx = await base_context(request, db)
    ctx.update({
        "stats": stats,
        "popular_routes": popular,
        "top_airlines": airlines,
        "cities": cities,
        "bookings_by_day": bookings_by_day,
        "avg_prices": avg_prices,
        "status_breakdown": status_breakdown,
    })
    return templates.TemplateResponse(request, "admin.html", ctx)


# ---------- Профиль пользователя ----------
@router.get("/profile", response_class=HTMLResponse, summary="Профиль пользователя")
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/profile", status_code=303)

    bookings = await get_user_bookings(db, user.id)
    favorites = await get_user_favorites(db, user.id)

    # Считаем простую статистику пользователя
    total_spent = sum(
        b.total_price for b in bookings if b.status != BookingStatus.CANCELLED
    )
    active_bookings = [b for b in bookings if b.status != BookingStatus.CANCELLED]
    cancelled_bookings = [b for b in bookings if b.status == BookingStatus.CANCELLED]

    ctx = await base_context(request, db)
    ctx.update({
        "user_bookings": bookings,
        "favorites_count": len(favorites),
        "total_spent": total_spent,
        "active_bookings_count": len(active_bookings),
        "cancelled_bookings_count": len(cancelled_bookings),
    })
    return templates.TemplateResponse(request, "profile.html", ctx)


# ---------- Избранные рейсы (HTML) ----------
@router.get("/favorites", response_class=HTMLResponse, summary="Избранные рейсы")
async def favorites_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/favorites", status_code=303)

    favorites = await get_user_favorites(db, user.id)
    ctx = await base_context(request, db)
    ctx.update({"flights": favorites, "is_favorites_page": True})
    return templates.TemplateResponse(request, "favorites.html", ctx)


@router.post("/favorites/{flight_id}/add", summary="Добавить в избранное (форма)")
async def favorites_add(
    request: Request,
    flight_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    await add_favorite(db, user.id, flight_id)
    await db.commit()
    return RedirectResponse(url="/favorites", status_code=303)


@router.post("/favorites/{flight_id}/remove", summary="Удалить из избранного (форма)")
async def favorites_remove(
    request: Request,
    flight_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    await remove_favorite(db, user.id, flight_id)
    await db.commit()
    return RedirectResponse(url="/favorites", status_code=303)


# ---------- История поиска (HTML) ----------
@router.get("/search-history", response_class=HTMLResponse, summary="История поиска")
async def search_history_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/search-history", status_code=303)

    history = await get_user_search_history(db, user.id, limit=20)
    ctx = await base_context(request, db)
    ctx.update({"history": history})
    return templates.TemplateResponse(request, "search_history.html", ctx)


# ---------- Подтверждение бронирования ----------
@router.post("/booking/{code}/confirm", summary="Подтвердить бронирование")
async def confirm_booking(
    request: Request,
    code: str,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    booking = await update_booking_status(db, code, BookingStatus.CONFIRMED)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    await db.commit()
    return RedirectResponse(
        url=f"/booking/{code}/view?toast={('Бронирование подтверждено')}&toast_type=success",
        status_code=303,
    )


@router.post("/booking/{code}/cancel", summary="Отменить бронирование")
async def cancel_booking(
    request: Request,
    code: str,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    booking = await update_booking_status(db, code, BookingStatus.CANCELLED)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    await db.commit()
    return RedirectResponse(
        url=f"/booking/{code}/view?toast={('Бронирование отменено')}&toast_type=error",
        status_code=303,
    )


# ---------- Страница сброса пароля ----------
@router.get("/reset", response_class=HTMLResponse, summary="Сброс пароля")
async def reset_password_page(
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Страница запроса сброса пароля или установки нового (если есть ?token=)."""
    ctx = await base_context(request, db)
    ctx.update({"token": token})
    return templates.TemplateResponse(request, "reset_password.html", ctx)


# ---------- Страница аудит-лога ----------
@router.get("/admin/audit", response_class=HTMLResponse, summary="Аудит-лог")
async def audit_log_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Страница просмотра аудита действий администраторов."""
    user = await get_user_from_request(request, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    logs = await get_audit_logs(db, limit=50)
    ctx = await base_context(request, db)
    ctx.update({"logs": logs})
    return templates.TemplateResponse(request, "audit_log.html", ctx)
