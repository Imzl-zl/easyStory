from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.service import AuthLoginDTO, AuthRegisterDTO, AuthService, AuthTokenDTO
from app.modules.user.entry.http.dependencies import get_auth_service
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenDTO)
async def register(
    payload: AuthRegisterDTO,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_async_db_session),
) -> AuthTokenDTO:
    return await auth_service.register(db, payload)


@router.post("/login", response_model=AuthTokenDTO)
async def login(
    payload: AuthLoginDTO,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_async_db_session),
) -> AuthTokenDTO:
    return await auth_service.login(db, payload)
