from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.models import ModelCredential
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
        interop_profile: str | None,
        auth_strategy: str | None,
        api_key_header_name: str | None,
        extra_headers: dict[str, str] | None,
        user_agent_override: str | None,
        client_name: str | None,
        client_version: str | None,
        runtime_kind: str | None,
        probe_kind: str | None,
        transport_mode: str | None,
    ) -> CredentialVerificationResult:
        assert provider
        assert api_key
        assert api_dialect
        assert default_model
        assert interop_profile is None or interop_profile
        assert user_agent_override is None or user_agent_override
        assert client_name is None or client_name
        assert client_version is None or client_version
        assert runtime_kind is None or runtime_kind
        assert probe_kind in {
            "text_probe",
            "tool_definition_probe",
            "tool_call_probe",
            "tool_continuation_probe",
        }
        assert transport_mode in {None, "stream", "buffered"}
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="验证成功",
            probe_kind=probe_kind or "text_probe",
            transport_mode=transport_mode,
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
    assert updated.last_verified_at is None
    assert updated.stream_tool_verified_probe_kind is None
    assert updated.buffered_tool_verified_probe_kind is None


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


def test_create_credential_persists_interop_profile_override(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                api_dialect="openai_chat_completions",
                interop_profile="chat_compat_reasoning_content",
            ),
            actor_user_id=user.id,
        )
    )

    assert created.interop_profile == "chat_compat_reasoning_content"


def test_create_credential_normalizes_default_interop_profile_to_none(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                api_dialect="openai_chat_completions",
                interop_profile="chat_compat_plain",
            ),
            actor_user_id=user.id,
        )
    )

    assert created.interop_profile is None


def test_create_credential_persists_client_identity(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                client_name=" easyStory ",
                client_version=" 0.1 ",
                runtime_kind="server-python",
            ),
            actor_user_id=user.id,
        )
    )

    assert created.client_name == "easyStory"
    assert created.client_version == "0.1"
    assert created.runtime_kind == "server-python"


def test_create_credential_persists_user_agent_override(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(user_agent_override=" codex-cli/0.118.0 (server; node) "),
            actor_user_id=user.id,
        )
    )

    assert created.user_agent_override == "codex-cli/0.118.0 (server; node)"


def test_update_credential_can_clear_client_identity(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                client_name="easyStory",
                client_version="0.1",
                runtime_kind="server-python",
            ),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(
                client_name="",
                client_version="",
                runtime_kind=None,
            ),
            actor_user_id=user.id,
        )
    )

    assert updated.client_name is None
    assert updated.client_version is None
    assert updated.runtime_kind is None


def test_update_credential_can_clear_user_agent_override(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(user_agent_override="codex-cli/0.118.0 (server; node)"),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(user_agent_override=""),
            actor_user_id=user.id,
        )
    )

    assert updated.user_agent_override is None


def test_update_credential_rejects_client_version_without_client_name(db, monkeypatch) -> None:
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

    with pytest.raises(ConfigurationError, match="client_name is required"):
        asyncio.run(
            service.update_credential(
                async_db(db),
                credential.id,
                CredentialUpdateDTO(client_version="0.1"),
                actor_user_id=user.id,
            )
        )


def test_create_credential_persists_token_limits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                context_window_tokens=128000,
                default_max_output_tokens=8192,
            ),
            actor_user_id=user.id,
        )
    )

    assert created.context_window_tokens == 128000
    assert created.default_max_output_tokens == 8192


def test_update_credential_can_clear_token_limits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                context_window_tokens=128000,
                default_max_output_tokens=8192,
            ),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(
                context_window_tokens=None,
                default_max_output_tokens=None,
            ),
            actor_user_id=user.id,
        )
    )

    assert updated.context_window_tokens is None
    assert updated.default_max_output_tokens is None


def test_update_credential_can_change_and_clear_interop_profile(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                api_dialect="openai_chat_completions",
                interop_profile="chat_compat_reasoning_content",
            ),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(interop_profile="chat_compat_usage_extra_chunk"),
            actor_user_id=user.id,
        )
    )
    cleared = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(interop_profile=None),
            actor_user_id=user.id,
        )
    )

    assert updated.interop_profile == "chat_compat_usage_extra_chunk"
    assert cleared.interop_profile is None


def test_update_credential_clears_verification_state_on_connection_change(db, monkeypatch) -> None:
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
    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    stored.last_verified_at = datetime.now(timezone.utc)
    stored.stream_tool_verified_probe_kind = "tool_continuation_probe"
    stored.stream_tool_last_verified_at = stored.last_verified_at
    stored.buffered_tool_verified_probe_kind = "tool_call_probe"
    stored.buffered_tool_last_verified_at = stored.last_verified_at
    db.add(stored)
    db.commit()

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(default_model="gpt-4.1-mini"),
            actor_user_id=user.id,
        )
    )

    assert updated.last_verified_at is None
    assert updated.stream_tool_verified_probe_kind is None
    assert updated.stream_tool_last_verified_at is None
    assert updated.buffered_tool_verified_probe_kind is None
    assert updated.buffered_tool_last_verified_at is None


def test_create_credential_rejects_incompatible_interop_profile_for_dialect(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="not supported for api_dialect"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(
                    api_dialect="anthropic_messages",
                    interop_profile="chat_compat_reasoning_content",
                ),
                actor_user_id=user.id,
            )
        )


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


def test_create_credential_rejects_runtime_managed_user_agent_header(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(ConfigurationError, match="runtime-managed headers"):
        asyncio.run(
            service.create_credential(
                async_db(db),
                _create_payload(extra_headers={"User-Agent": "fake-cli/1.0"}),
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
