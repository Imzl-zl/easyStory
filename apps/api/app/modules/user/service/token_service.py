from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.shared.runtime.errors import ConfigurationError, UnauthorizedError
from app.shared.settings import JWT_EXPIRE_HOURS_ENV, JWT_SECRET_ENV, get_settings

JWT_ALGORITHM = "HS256"


class TokenService:
    def __init__(
        self,
        *,
        secret: str | None = None,
        expire_hours: int | None = None,
    ) -> None:
        self.secret = self._resolve_secret(secret)
        self.expire_hours = self._resolve_expire_hours(expire_hours)

    def issue_for_user(self, user_id: uuid.UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=self.expire_hours)).timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm=JWT_ALGORITHM)

    def read_user_id(self, token: str) -> uuid.UUID:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[JWT_ALGORITHM])
            return uuid.UUID(payload["sub"])
        except (JWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError("Invalid authentication credentials") from exc

    def _resolve_secret(self, secret: str | None) -> str:
        if secret is not None:
            if secret.strip():
                return secret
            raise ConfigurationError(f"{JWT_SECRET_ENV} must be a non-empty string")
        return get_settings().require_jwt_secret()

    def _resolve_expire_hours(self, expire_hours: int | None) -> int:
        if expire_hours is not None:
            if expire_hours <= 0:
                raise ConfigurationError(f"{JWT_EXPIRE_HOURS_ENV} must be > 0")
            return expire_hours
        configured_expire_hours = get_settings().jwt_expire_hours
        if configured_expire_hours <= 0:
            raise ConfigurationError(f"{JWT_EXPIRE_HOURS_ENV} must be > 0")
        return configured_expire_hours
