from __future__ import annotations

import uuid

import pytest

from app.modules.user.service import TokenService
from app.shared.runtime.errors import ConfigurationError
from app.shared.settings import JWT_EXPIRE_HOURS_ENV


def test_token_service_uses_explicit_values_without_loading_settings(monkeypatch) -> None:
    monkeypatch.setenv(JWT_EXPIRE_HOURS_ENV, "bad")

    token = TokenService(secret="manual-secret", expire_hours=1).issue_for_user(uuid.uuid4())

    assert token


def test_token_service_rejects_empty_explicit_secret() -> None:
    with pytest.raises(ConfigurationError, match="EASYSTORY_JWT_SECRET"):
        TokenService(secret="", expire_hours=1)
