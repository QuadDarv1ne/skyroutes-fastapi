"""API сброса пароля: запрос токена и установка нового пароля."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_password_reset_token,
    get_user_by_email,
    use_password_reset_token,
    verify_password_reset_token,
)
from app.database import get_db
from app.models import User
from app.config import settings
import logging

logger = logging.getLogger("skyroutes.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запросить сброс пароля",
)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Запрос на сброс пароля. Всегда возвращает 202, чтобы не раскрывать
    существование email в базе (защита от перебора)."""
    user = await get_user_by_email(db, payload.email)
    if user:
        token = await create_password_reset_token(db, user)
        await db.commit()
        # В реальном проекте здесь отправляли бы email через SMTP/SendGrid
        # В демо-режиме просто логируем (а в DEBUG — возвращаем токен в ответе)
        logger.info(
            "Password reset requested for %s from %s. Token (demo only): /reset?token=%s",
            user.email,
            request.client.host if request.client else "unknown",
            token,
        )
        if settings.debug:
            return {
                "message": "Если email существует, инструкция отправлена.",
                "demo_reset_url": f"/reset?token={token}",
            }
    return {"message": "Если email существует, инструкция отправлена."}


@router.post(
    "/password-reset/confirm",
    summary="Установить новый пароль по токену",
)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Установка нового пароля по валидному токену сброса."""
    user = await verify_password_reset_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    ok = await use_password_reset_token(db, payload.token, payload.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset password",
        )
    await db.commit()
    logger.info("Password reset successful for user %s", user.email)
    return {"message": "Password has been reset successfully. Please login."}
