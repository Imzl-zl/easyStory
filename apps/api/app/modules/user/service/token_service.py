from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.shared.runtime.errors import ConfigurationError, UnauthorizedError

JWT_ALGORITHM = "HS256"
JWT_SECRET_ENV = "EASYSTORY_JWT_SECRET"
JWT_EXPIRE_HOURS_ENV = "EASYSTORY_JWT_EXPIRE_HOURS"
DEFAULT_JWT_EXPIRE_HOURS = 24


class TokenService:
    def __init__(self) -> None:
        self.secret = self._load_secret()
        self.expire_hours = self._load_expire_hours()

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

    def _load_secret(self) -> str:
        secret = os.getenv(JWT_SECRET_ENV)
        if not secret:
            raise ConfigurationError(f"Missing required environment variable: {JWT_SECRET_ENV}")
        return secret

    def _load_expire_hours(self) -> int:
        raw_value = os.getenv(JWT_EXPIRE_HOURS_ENV, str(DEFAULT_JWT_EXPIRE_HOURS))
        try:
            expire_hours = int(raw_value)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid integer for {JWT_EXPIRE_HOURS_ENV}: {raw_value}"
            ) from exc
        if expire_hours <= 0:
            raise ConfigurationError(f"{JWT_EXPIRE_HOURS_ENV} must be > 0")
        return expire_hours
