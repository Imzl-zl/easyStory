from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.modules.user.models import User
from app.modules.user.service import (
    AuthService,
    TokenService,
    create_auth_service,
    create_token_service,
)
from app.shared.db import get_db_session
from app.shared.runtime.errors import UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_service() -> TokenService:
    return create_token_service()


def get_auth_service(
    token_service: TokenService = Depends(get_token_service),
) -> AuthService:
    return create_auth_service(token_service=token_service)


def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required")
    return auth_service.authenticate(db, credentials.credentials)
