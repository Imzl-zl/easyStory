from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.settings import (
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    CORS_ALLOWED_ORIGIN_REGEX_ENV,
    EasyStorySettings,
    JWT_EXPIRE_HOURS_ENV,
)


def test_settings_loads_env_file_values(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "EASYSTORY_JWT_SECRET=test-secret",
                "EASYSTORY_JWT_EXPIRE_HOURS=12",
                "EASYSTORY_CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000, http://localhost:3001",
            ]
        ),
        encoding="utf-8",
    )

    settings = EasyStorySettings(_env_file=env_file)

    assert settings.require_jwt_secret() == "test-secret"
    assert settings.jwt_expire_hours == 12
    assert settings.cors_allowed_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]


def test_settings_require_jwt_secret_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("EASYSTORY_JWT_SECRET", raising=False)
    settings = EasyStorySettings(_env_file=None)

    with pytest.raises(ConfigurationError, match="EASYSTORY_JWT_SECRET"):
        settings.require_jwt_secret()


def test_settings_reads_custom_origin_regex(monkeypatch) -> None:
    regex = r"^https://example\.com$"
    monkeypatch.setenv(JWT_EXPIRE_HOURS_ENV, "12")
    monkeypatch.setenv(CORS_ALLOWED_ORIGIN_REGEX_ENV, regex)

    settings = EasyStorySettings(_env_file=None)

    assert settings.cors_allowed_origin_regex == regex


def test_settings_rejects_non_positive_expire_hours(monkeypatch) -> None:
    monkeypatch.setenv(JWT_EXPIRE_HOURS_ENV, "0")

    with pytest.raises(ConfigurationError, match=JWT_EXPIRE_HOURS_ENV):
        EasyStorySettings(_env_file=None)


def test_settings_rejects_non_integer_expire_hours(monkeypatch) -> None:
    monkeypatch.setenv(JWT_EXPIRE_HOURS_ENV, "bad")

    with pytest.raises(ConfigurationError, match=JWT_EXPIRE_HOURS_ENV):
        EasyStorySettings(_env_file=None)


def test_settings_parses_private_endpoint_toggle(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "true")

    settings = EasyStorySettings(_env_file=None)

    assert settings.allow_private_model_endpoints is True


def test_settings_rejects_invalid_private_endpoint_toggle(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "maybe")

    with pytest.raises(ConfigurationError, match=ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV):
        EasyStorySettings(_env_file=None)
