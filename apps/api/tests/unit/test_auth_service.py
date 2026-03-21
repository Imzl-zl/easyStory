from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, Mock

from app.modules.user.service.auth_service import AuthService
from app.modules.user.service.dto import AuthRegisterDTO
from app.shared.runtime.errors import ConflictError


class DummyTokenService:
    def issue_for_user(self, _user_id) -> str:
        return "token"


async def test_auth_register_translates_integrity_error_to_conflict(monkeypatch):
    service = AuthService(DummyTokenService())
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
    db.rollback = AsyncMock()
    monkeypatch.setattr(service, "_ensure_username_available", AsyncMock(return_value=None))

    with pytest.raises(ConflictError):
        await service.register(
            db,
            AuthRegisterDTO(username="writer_user", password="password123"),
        )

    db.rollback.assert_awaited_once()
