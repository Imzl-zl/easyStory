from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.main import create_app
from app.modules.credential.entry.http.router import get_credential_service
from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.service import create_credential_service
from app.modules.project.models import Project
from app.shared.settings import clear_settings_cache
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"
OPENAI_DIALECT = "openai_chat_completions"
OPENAI_MODEL = "gpt-4o-mini"


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
    ) -> CredentialVerificationResult:
        assert provider == "openai"
        assert api_key == "sk-secret-1234"
        assert base_url is None
        assert api_dialect == OPENAI_DIALECT
        assert default_model == OPENAI_MODEL
        assert interop_profile == "chat_compat_reasoning_content"
        assert auth_strategy == "custom_header"
        assert api_key_header_name == "api-key"
        assert extra_headers == {"X-Trace-Id": "api-check"}
        assert user_agent_override == "codex-cli/0.118.0 (server; node)"
        assert client_name == "easyStory"
        assert client_version == "0.1"
        assert runtime_kind == "server-python"
        assert probe_kind == "tool_continuation_probe"
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="工具调用验证成功",
            probe_kind="tool_continuation_probe",
        )


async def test_credentials_api_create_list_and_verify(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    clear_settings_cache()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-api-success")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        app.dependency_overrides[get_credential_service] = lambda: create_credential_service(
            verifier=FakeVerifier()
        )
        owner_id = _seed_owner(session_factory)
        headers = _auth_headers(owner_id)

        async with started_async_client(app) as client:
            create_response = await client.post(
                "/api/v1/credentials",
                json={
                    "owner_type": "user",
                    "provider": "openai",
                    "display_name": "我的 OpenAI",
                    "api_key": "sk-secret-1234",
                    "default_model": OPENAI_MODEL,
                    "interop_profile": "chat_compat_reasoning_content",
                    "context_window_tokens": 128000,
                    "default_max_output_tokens": 8192,
                    "auth_strategy": "custom_header",
                    "api_key_header_name": "api-key",
                    "extra_headers": {"X-Trace-Id": "api-check"},
                    "user_agent_override": "codex-cli/0.118.0 (server; node)",
                    "client_name": "easyStory",
                    "client_version": "0.1",
                    "runtime_kind": "server-python",
                },
                headers=headers,
            )
            assert create_response.status_code == 200
            payload = create_response.json()
            assert payload["provider"] == "openai"
            assert payload["api_dialect"] == OPENAI_DIALECT
            assert payload["default_model"] == OPENAI_MODEL
            assert payload["interop_profile"] == "chat_compat_reasoning_content"
            assert payload["verified_probe_kind"] is None
            assert payload["context_window_tokens"] == 128000
            assert payload["default_max_output_tokens"] == 8192
            assert payload["auth_strategy"] == "custom_header"
            assert payload["api_key_header_name"] == "api-key"
            assert payload["extra_headers"] == {"X-Trace-Id": "api-check"}
            assert payload["user_agent_override"] == "codex-cli/0.118.0 (server; node)"
            assert payload["client_name"] == "easyStory"
            assert payload["client_version"] == "0.1"
            assert payload["runtime_kind"] == "server-python"
            assert payload["masked_key"] == "sk-...1234"

            list_response = await client.get("/api/v1/credentials", headers=headers)
            assert list_response.status_code == 200
            assert len(list_response.json()) == 1

            verify_response = await client.post(
                f"/api/v1/credentials/{payload['id']}/verify?probe_kind=tool_continuation_probe",
                headers=headers,
            )

        assert verify_response.status_code == 200
        assert verify_response.json()["message"] == "工具调用验证成功"
        assert verify_response.json()["probe_kind"] == "tool_continuation_probe"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_credentials_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    clear_settings_cache()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-api-owner")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        project_id, _owner_id = _seed_project(session_factory)
        outsider_id = _seed_owner(session_factory)

        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/credentials",
                json={
                    "owner_type": "project",
                    "project_id": project_id,
                    "provider": "openai",
                    "display_name": "项目 Key",
                    "api_key": "sk-secret-1234",
                    "default_model": OPENAI_MODEL,
                },
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_credentials_api_returns_configuration_error_when_master_key_missing(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", "")
    clear_settings_cache()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-api-config")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        owner_id = _seed_owner(session_factory)

        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/credentials",
                json={
                    "owner_type": "user",
                    "provider": "openai",
                    "display_name": "我的 OpenAI",
                    "api_key": "sk-secret-1234",
                    "default_model": OPENAI_MODEL,
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_project(session_factory) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        project = Project(name="API 测试项目", owner_id=owner.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        return str(project.id), owner.id


def _seed_owner(session_factory) -> uuid.UUID:
    with session_factory() as session:
        return create_user(session).id
