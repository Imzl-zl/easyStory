from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.user.service.auth_service import AuthService
from app.modules.user.service.dto import AuthRegisterDTO
from app.shared.runtime.errors import ConflictError


class DummyTokenService:
    def issue_for_user(self, _user_id) -> str:
        return "token"


def test_auth_register_translates_integrity_error_to_conflict(db, monkeypatch):
    service = AuthService(DummyTokenService())
    rollback_called = {"value": False}

    def fake_commit() -> None:
        raise IntegrityError("insert", {}, Exception("duplicate"))

    def fake_rollback() -> None:
        rollback_called["value"] = True

    monkeypatch.setattr(db, "commit", fake_commit)
    monkeypatch.setattr(db, "rollback", fake_rollback)

    with pytest.raises(ConflictError):
        service.register(
            db,
            AuthRegisterDTO(username="writer_user", password="password123"),
        )

    assert rollback_called["value"] is True
