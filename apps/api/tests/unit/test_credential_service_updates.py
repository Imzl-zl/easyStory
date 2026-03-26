from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.service import (
    CredentialCreateDTO,
    CredentialUpdateDTO,
    create_credential_service,
)
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"
OPENAI_MODEL = "gpt-4o-mini"
PUBLIC_BASE_URL = "https://proxy.example.com/openai/v1"
PRIVATE_BASE_URL = "http://127.0.0.1:11434/v1"


class FakeVerifier:
    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        auth_strategy: str | None,
        api_key_header_name: str | None,
        extra_headers: dict[str, str] | None,
    ) -> CredentialVerificationResult:
        assert provider
        assert api_key
        assert api_dialect
        assert default_model
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="Credential verified",
        )


def _create_payload(**overrides) -> CredentialCreateDTO:
    payload = {
        "owner_type": "user",
        "provider": "openai",
        "display_name": "我的 OpenAI Key",
        "api_key": "sk-secret-1234",
        "default_model": OPENAI_MODEL,
    }
    payload.update(overrides)
    return CredentialCreateDTO(**payload)


def test_create_credential_rejects_private_base_url_by_default(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="Private or local model endpoints are disabled"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(base_url=PRIVATE_BASE_URL),
                actor_user_id=user.id,
            )
        )


def test_update_credential_clears_base_url_when_explicitly_null(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(base_url=PUBLIC_BASE_URL),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(base_url=None),
            actor_user_id=user.id,
        )
    )

    assert updated.base_url is None


def test_update_credential_rejects_explicit_null_default_model(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(),
            actor_user_id=user.id,
        )
    )

    with pytest.raises(ConfigurationError, match="default_model cannot be null"):
        asyncio.run(
            service.update_credential(
                async_db(db),
                credential.id,
                CredentialUpdateDTO(default_model=None),
                actor_user_id=user.id,
            )
        )


def test_create_credential_persists_connection_overrides(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                api_dialect="openai_chat_completions",
                auth_strategy="custom_header",
                api_key_header_name="api-key",
                extra_headers={"X-Trace-Id": "story-run"},
            ),
            actor_user_id=user.id,
        )
    )

    assert created.auth_strategy == "custom_header"
    assert created.api_key_header_name == "api-key"
    assert created.extra_headers == {"X-Trace-Id": "story-run"}


def test_update_credential_rejects_runtime_managed_extra_headers(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(),
            actor_user_id=user.id,
        )
    )

    with pytest.raises(ConfigurationError, match="runtime-managed headers"):
        asyncio.run(
            service.update_credential(
                async_db(db),
                credential.id,
                CredentialUpdateDTO(extra_headers={"Authorization": "Bearer override"}),
                actor_user_id=user.id,
            )
        )


def test_create_credential_rejects_runtime_managed_custom_auth_header(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="api_key_header_name cannot override runtime-managed headers"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(
                    api_dialect="anthropic_messages",
                    auth_strategy="custom_header",
                    api_key_header_name="anthropic-version",
                ),
                actor_user_id=user.id,
            )
        )


def test_create_credential_rejects_sensitive_extra_headers(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="extra_headers only support non-sensitive metadata headers"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(extra_headers={"X-Auth-Token": "secret-token"}),
                actor_user_id=user.id,
            )
        )


def test_create_credential_rejects_non_token_http_header_name(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="valid HTTP header name"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(
                    api_dialect="openai_chat_completions",
                    auth_strategy="custom_header",
                    api_key_header_name="bad@header",
                ),
                actor_user_id=user.id,
            )
        )
