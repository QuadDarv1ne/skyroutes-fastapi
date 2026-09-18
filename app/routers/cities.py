"""API справочника городов."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import get_cities
from app.database import get_db
from app.schemas import CityRead


router = APIRouter(prefix="/api/cities", tags=["cities"])


@router.get("", response_model=list[CityRead], summary="Список городов/аэропортов")
async def list_cities(db: AsyncSession = Depends(get_db)) -> list[CityRead]:
    cities = await get_cities(db)
    return [CityRead.model_validate(c) for c in cities]
