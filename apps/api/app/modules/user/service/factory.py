from __future__ import annotations

from .auth_service import AuthService
from .token_service import TokenService


def create_token_service() -> TokenService:
    return TokenService()


def create_auth_service(
    *,
    token_service: TokenService | None = None,
) -> AuthService:
    return AuthService(token_service or create_token_service())
