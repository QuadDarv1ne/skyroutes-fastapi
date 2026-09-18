"""API избранных рейсов пользователя.

Все эндпоинты требуют JWT-аутентификации.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    add_favorite,
    get_user_favorites,
    remove_favorite,
)
from app.database import get_db
from app.models import User
from app.schemas import FlightRead
from app.security import require_user


router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[FlightRead], summary="Избранные рейсы пользователя")
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> list[FlightRead]:
    flights = await get_user_favorites(db, user.id)
    return [FlightRead.model_validate(f) for f in flights]


@router.post(
    "/{flight_id}",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить рейс в избранное",
)
async def add_to_favorites(
    flight_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> dict:
    fav = await add_favorite(db, user.id, flight_id)
    if fav is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already in favorites or flight not found",
        )
    await db.commit()
    return {"status": "added", "flight_id": flight_id}


@router.delete(
    "/{flight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить рейс из избранного",
)
async def remove_from_favorites(
    flight_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    ok = await remove_favorite(db, user.id, flight_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.commit()
