from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.models import User
from app.modules.user.service import (
    AuthService,
    TokenService,
    create_auth_service,
    create_token_service,
)
from app.shared.db import get_async_db_session
from app.shared.runtime.errors import ForbiddenError, UnauthorizedError
from app.shared.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_service() -> TokenService:
    return create_token_service()


async def get_auth_service(
    token_service: TokenService = Depends(get_token_service),
) -> AuthService:
    return create_auth_service(token_service=token_service)


async def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required")
    return await auth_service.authenticate(db, credentials.credentials)


def ensure_config_admin(current_user: User) -> User:
    return ensure_control_plane_admin(current_user)


def ensure_control_plane_admin(current_user: User) -> User:
    if get_settings().is_config_admin(current_user.username):
        return current_user
    raise ForbiddenError("Control-plane admin access required")


async def require_control_plane_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    return ensure_control_plane_admin(current_user)


async def require_config_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    return ensure_control_plane_admin(current_user)
