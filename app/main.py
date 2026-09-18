"""FastAPI приложение: точки входа, статика, middleware, события жизненного цикла."""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers import (
    flights,
    bookings,
    cities,
    pages,
    auth,
    admin,
    favorites,
    search_history,
    password_reset,
)


# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("skyroutes")
access_logger = logging.getLogger("skyroutes.access")


# ---------- Rate limiter ----------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создаём таблицы при старте приложения (для разработки)."""
    logger.info("Initializing database...")
    await init_db()
    logger.info(
        "SkyRoutes app started: %s v%s", settings.app_name, settings.app_version
    )
    yield
    logger.info("SkyRoutes app shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    description=(
        "Заготовка сайта путешествий: поиск рейсов, бронирование, "
        "JWT-аутентификация, админ-панель, статистика, rate limiting и история поиска."
    ),
)

# ---------- Rate limiter state ----------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- GZip сжатие ----------
# Сжимает ответы больше 500 байт (HTML, JSON) — экономит трафик
app.add_middleware(GZipMiddleware, minimum_size=500)


# ---------- Middleware логирования запросов ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует каждый HTTP-запрос с методом, путём, статусом и длительностью."""
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Пропускаем логирование статики и health-check (шумят)
    path = request.url.path
    if path.startswith("/static") or path == "/api/health" or path == "/favicon.ico":
        return response

    access_logger.info(
        "%s %s → %d (%.0fms) [%s]",
        request.method,
        path,
        response.status_code,
        duration_ms,
        request.headers.get("user-agent", "-")[:60],
    )
    return response


# ---------- Статика ----------
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

# Шаблоны для страниц ошибок
error_templates = Jinja2Templates(directory="app/templates")

# Роутеры
app.include_router(auth.router)
app.include_router(password_reset.router)
app.include_router(cities.router)
app.include_router(flights.router)
app.include_router(bookings.router)
app.include_router(favorites.router)
app.include_router(search_history.router)
app.include_router(admin.router)
app.include_router(pages.router)


# ---------- Обработчики ошибок ----------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Кастомная обработка HTTP-ошибок (404, 403, ...)."""
    if request.url.path.startswith(
        "/api/"
    ) or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status_code": exc.status_code},
        )
    template_name = "404.html" if exc.status_code == 404 else "error.html"
    return error_templates.TemplateResponse(
        request,
        template_name,
        {
            "request": request,
            "settings": settings,
            "current_user": None,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Логируем и прячем стек для необработанных исключений."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )
    return error_templates.TemplateResponse(
        request,
        "error.html",
        {
            "request": request,
            "settings": settings,
            "current_user": None,
            "status_code": 500,
            "detail": "Внутренняя ошибка сервера",
        },
        status_code=500,
    )


# ---------- Метрики (без зависимостей) ----------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Считает запросы по методу и статусу в in-memory счётчике."""
    response: Response = await call_next(request)
    if not hasattr(app.state, "request_counts"):
        app.state.request_counts = {}
    key = f"{request.method}:{response.status_code}"
    app.state.request_counts[key] = app.state.request_counts.get(key, 0) + 1
    return response


@app.get("/api/health", tags=["meta"], summary="Проверка работоспособности")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/api/health/detailed", tags=["meta"], summary="Детальный health-check")
async def health_detailed() -> dict:
    """Проверка работоспособности с зависимостями (БД)."""
    from sqlalchemy import text
    from app.database import engine

    db_status = "ok"
    db_error = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        db_status = "error"
        db_error = str(e)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "dependencies": {
            "database": {
                "status": db_status,
                "error": db_error,
                "url": settings.database_url.split("://")[0] + "://***",
            },
        },
        "timestamp": time.time(),
    }


@app.get("/api/metrics", tags=["meta"], summary="Метрики запросов")
async def metrics() -> dict:
    """Простые in-memory счётчики запросов по методу и статусу."""
    return {
        "request_counts": getattr(app.state, "request_counts", {}),
        "version": settings.app_version,
    }


@app.get("/api", tags=["meta"], summary="Корневой API endpoint")
async def api_root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "auth": "/api/auth/register, /api/auth/login, /api/auth/me",
            "password_reset": "/api/auth/password-reset/request, /confirm (новое!)",
            "cities": "/api/cities",
            "flights_search": "/api/flights (+ sorting, pagination)",
            "booking_create": "/api/bookings",
            "my_bookings": "/api/bookings?email=...",
            "favorites": "/api/favorites",
            "search_history": "/api/search-history",
            "admin_stats": "/api/admin/stats",
            "admin_flights": "/api/admin/flights",
            "admin_audit": "/api/admin/audit (новое!)",
            "metrics": "/api/metrics",
            "docs": "/docs",
            "home_page": "/",
        },
    }
