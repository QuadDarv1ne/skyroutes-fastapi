"""Конфигурация приложения."""
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Настройки приложения, читаемые из окружения или .env.

    Каждая переменная может быть задана как с префиксом TRAVEL_, так и без него:
    TRAVEL_DATABASE_URL имеет приоритет над DATABASE_URL.
    """

    app_name: str = Field(
        default="SkyRoutes — Путешествия и Авиаперелёты",
        validation_alias=AliasChoices("TRAVEL_APP_NAME", "APP_NAME"),
    )
    app_version: str = Field(
        default="0.2.0",
        validation_alias=AliasChoices("TRAVEL_APP_VERSION", "APP_VERSION"),
    )
    debug: bool = Field(
        default=True,
        validation_alias=AliasChoices("TRAVEL_DEBUG", "DEBUG"),
    )

    # SQLite по умолчанию (для разработки).
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{BASE_DIR / 'travel.db'}",
        validation_alias=AliasChoices("TRAVEL_DATABASE_URL", "DATABASE_URL"),
    )

    currency: str = Field(
        default="RUB",
        validation_alias=AliasChoices("TRAVEL_CURRENCY", "CURRENCY"),
    )
    currency_symbol: str = Field(
        default="₽",
        validation_alias=AliasChoices("TRAVEL_CURRENCY_SYMBOL", "CURRENCY_SYMBOL"),
    )
    page_size: int = Field(
        default=10,
        validation_alias=AliasChoices("TRAVEL_PAGE_SIZE", "PAGE_SIZE"),
    )

    # JWT / безопасность — ОБЯЗАТЕЛЬНО поменяй secret_key в продакшене
    secret_key: str = Field(
        default="change-me-in-production-please-use-long-random-string",
        validation_alias=AliasChoices("TRAVEL_SECRET_KEY", "SECRET_KEY"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("TRAVEL_JWT_ALGORITHM", "JWT_ALGORITHM"),
    )
    access_token_expire_minutes: int = Field(
        default=60 * 24,
        validation_alias=AliasChoices("TRAVEL_ACCESS_TOKEN_EXPIRE_MINUTES", "ACCESS_TOKEN_EXPIRE_MINUTES"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()