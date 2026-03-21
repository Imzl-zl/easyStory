from __future__ import annotations

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.models import User
from app.shared.runtime.errors import BusinessRuleError, ConflictError, UnauthorizedError

from .dto import AuthLoginDTO, AuthRegisterDTO, AuthTokenDTO
from .token_service import TokenService

MAX_BCRYPT_PASSWORD_BYTES = 72


class AuthService:
    def __init__(self, token_service: TokenService) -> None:
        self.token_service = token_service

    async def register(self, db: AsyncSession, payload: AuthRegisterDTO) -> AuthTokenDTO:
        await self._ensure_username_available(db, payload.username)
        _ensure_password_bytes_limit(payload.password)
        user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=_hash_password(payload.password),
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError(f"Username already exists: {payload.username}") from exc
        await db.refresh(user)
        return self._build_auth_token(user)

    async def login(self, db: AsyncSession, payload: AuthLoginDTO) -> AuthTokenDTO:
        user = await self._require_active_user_by_username(db, payload.username)
        if not _verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid username or password")
        return self._build_auth_token(user)

    async def authenticate(self, db: AsyncSession, token: str) -> User:
        user_id = self.token_service.read_user_id(token)
        user = await db.scalar(select(User).where(User.id == user_id))
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid authentication credentials")
        return user

    async def _ensure_username_available(self, db: AsyncSession, username: str) -> None:
        exists = await db.scalar(select(User.id).where(User.username == username))
        if exists is not None:
            raise ConflictError(f"Username already exists: {username}")

    async def _require_active_user_by_username(
        self,
        db: AsyncSession,
        username: str,
    ) -> User:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid username or password")
        return user

    def _build_auth_token(self, user: User) -> AuthTokenDTO:
        return AuthTokenDTO(
            access_token=self.token_service.issue_for_user(user.id),
            user_id=user.id,
            username=user.username,
        )


def _ensure_password_bytes_limit(password: str) -> None:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise BusinessRuleError("Password exceeds bcrypt byte limit")


def _hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def _verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
