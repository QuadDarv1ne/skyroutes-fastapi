"""API истории поисковых запросов пользователя."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import get_user_search_history
from app.database import get_db
from app.models import User
from app.security import require_user


router = APIRouter(prefix="/api/search-history", tags=["search-history"])


class SearchHistoryRead(BaseModel):
    id: int
    origin_code: Optional[str] = None
    destination_code: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    max_price: Optional[float] = None
    results_count: int
    created_at: object

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "",
    response_model=list[SearchHistoryRead],
    summary="История поиска пользователя",
)
async def list_search_history(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> list[SearchHistoryRead]:
    history = await get_user_search_history(db, user.id, limit=limit)
    return [SearchHistoryRead.model_validate(h) for h in history]
