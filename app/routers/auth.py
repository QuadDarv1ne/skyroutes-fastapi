"""API аутентификации: регистрация, логин, текущий пользователь."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_user, get_user_by_email
from app.database import get_db
from app.models import User
from app.schemas import TokenPair, UserCreate, UserRead
from app.security import create_access_token, get_current_user, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenPair, status_code=201, summary="Регистрация"
)
async def register(
    payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await create_user(db, payload.email, payload.password, payload.full_name)
    await db.commit()
    token = create_access_token(
        user.id, extra={"email": user.email, "admin": user.is_admin}
    )
    return TokenPair(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenPair, summary="Вход")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        user.id, extra={"email": user.email, "admin": user.is_admin}
    )
    return TokenPair(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead, summary="Текущий пользователь")
async def me(user: User = Depends(get_current_user)) -> UserRead:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserRead.model_validate(user)
