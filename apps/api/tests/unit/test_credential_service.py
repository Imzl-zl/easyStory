from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.modules.credential.infrastructure import (
    CredentialCrypto,
    CredentialVerificationResult,
)
from app.modules.credential.models import ModelCredential
from app.modules.credential.service import (
    CredentialCreateDTO,
    CredentialUpdateDTO,
    build_runtime_credential_payload,
    create_credential_service,
)
from app.modules.credential.service.credential_verification_support import (
    verify_credential_record,
)
from app.modules.observability.models import AuditLog
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"
OPENAI_DIALECT = "openai_chat_completions"
OPENAI_MODEL = "gpt-4o-mini"


class FakeVerifier:
    def __init__(
        self,
        verified_at: datetime | None = None,
        *,
        expected_probe_kind: str = "text_probe",
        expected_transport_mode: str | None = None,
    ) -> None:
        self.verified_at = verified_at or datetime.now(timezone.utc)
        self.expected_probe_kind = expected_probe_kind
        self.expected_transport_mode = expected_transport_mode

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
        assert base_url is None
        assert api_dialect == OPENAI_DIALECT
        assert default_model == OPENAI_MODEL
        assert interop_profile is None
        assert auth_strategy is None
        assert api_key_header_name is None
        assert extra_headers is None
        assert user_agent_override is None
        assert client_name is None
        assert client_version is None
        assert runtime_kind is None
        assert probe_kind == self.expected_probe_kind
        assert transport_mode == self.expected_transport_mode
        return CredentialVerificationResult(
            verified_at=self.verified_at,
            message="工具调用验证成功" if probe_kind == "tool_continuation_probe" else "验证成功",
            probe_kind=probe_kind or "text_probe",
            transport_mode=transport_mode,
        )


class FailingVerifier:
    def __init__(self, message: str = "工具调用验证失败") -> None:
        self.message = message

    async def verify(self, **_kwargs) -> CredentialVerificationResult:
        raise BusinessRuleError(self.message)


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


def test_credential_crypto_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()

    encrypted = crypto.encrypt("sk-secret-1234")

    assert encrypted != "sk-secret-1234"
    assert crypto.decrypt(encrypted) == "sk-secret-1234"


def test_build_runtime_credential_payload_is_reexported_from_service_package(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()
    credential = ModelCredential(
        owner_type="system",
        owner_id=None,
        provider="openai",
        api_dialect=OPENAI_DIALECT,
        display_name="系统",
        encrypted_key=crypto.encrypt("sk-service-1234"),
        default_model=OPENAI_MODEL,
    )

    payload = build_runtime_credential_payload(
        credential,
        decrypt_api_key=crypto.decrypt,
    )

    assert payload["api_key"] == "sk-service-1234"
    assert payload["api_dialect"] == OPENAI_DIALECT
    assert payload["default_model"] == OPENAI_MODEL


def test_create_user_credential_encrypts_and_audits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    result = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(provider="OpenAI"),
            actor_user_id=user.id,
        )
    )

    stored = db.query(ModelCredential).filter(ModelCredential.id == result.id).one()
    audits = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()

    assert stored.encrypted_key != "sk-secret-1234"
    assert result.provider == "openai"
    assert result.api_dialect == OPENAI_DIALECT
    assert result.default_model == OPENAI_MODEL
    assert result.interop_profile is None
    assert result.stream_tool_verified_probe_kind is None
    assert result.buffered_tool_verified_probe_kind is None
    assert result.context_window_tokens is None
    assert result.default_max_output_tokens is None
    assert result.auth_strategy is None
    assert result.api_key_header_name is None
    assert result.extra_headers is None
    assert result.user_agent_override is None
    assert result.client_name is None
    assert result.client_version is None
    assert result.runtime_kind is None
    assert result.masked_key == "sk-...1234"
    assert audits[-1].event_type == "credential_create"


def test_create_duplicate_provider_in_same_scope_conflicts(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    payload = _create_payload(display_name="OpenAI", api_key="sk-first-1234")
    asyncio.run(service.create_credential(async_db(db), payload, actor_user_id=user.id))

    with pytest.raises(ConflictError):
        asyncio.run(service.create_credential(async_db(db), payload, actor_user_id=user.id))


def test_project_credential_requires_owned_project(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(NotFoundError):
        asyncio.run(
                service.create_credential(
                    async_db(db),
                    _create_payload(
                        owner_type="project",
                        project_id=project.id,
                        display_name="项目 Key",
                    ),
                    actor_user_id=outsider.id,
                )
            )


def test_resolve_credential_prefers_project_then_user_then_system(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()
    user = create_user(db)
    project = create_project(db, owner=user, allow_system_credential_pool=True)
    service = create_credential_service(verifier=FakeVerifier(), crypto=crypto)
    system_credential = ModelCredential(
        owner_type="system",
        owner_id=None,
        provider="openai",
        api_dialect=OPENAI_DIALECT,
        display_name="系统",
        encrypted_key=crypto.encrypt("sk-system-1234"),
        default_model=OPENAI_MODEL,
    )
    user_credential = ModelCredential(
        owner_type="user",
        owner_id=user.id,
        provider="openai",
        api_dialect=OPENAI_DIALECT,
        display_name="用户",
        encrypted_key=crypto.encrypt("sk-user-1234"),
        default_model=OPENAI_MODEL,
    )
    project_credential = ModelCredential(
        owner_type="project",
        owner_id=project.id,
        provider="openai",
        api_dialect=OPENAI_DIALECT,
        display_name="项目",
        encrypted_key=crypto.encrypt("sk-project-1234"),
        default_model=OPENAI_MODEL,
    )
    db.add_all([system_credential, user_credential, project_credential])
    db.commit()

    resolved = asyncio.run(
        service.resolve_active_credential(
            async_db(db),
            provider="openai",
            user_id=user.id,
            project_id=project.id,
        )
    )
    assert resolved.id == project_credential.id
    db.delete(project_credential)
    db.commit()

    resolved = asyncio.run(
        service.resolve_active_credential(
            async_db(db),
            provider="openai",
            user_id=user.id,
            project_id=project.id,
        )
    )
    assert resolved.id == user_credential.id
    db.delete(user_credential)
    db.commit()

    resolved = asyncio.run(
        service.resolve_active_credential(
            async_db(db),
            provider="openai",
            user_id=user.id,
            project_id=project.id,
        )
    )
    assert resolved.id == system_credential.id


def test_list_credentials_keeps_creation_order_after_updates_and_verification(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    older = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(provider="openai", display_name="较早创建", api_key="sk-openai-1234"),
            actor_user_id=user.id,
        )
    )
    newer = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(provider="gemini", display_name="较晚创建", api_key="sk-gemini-1234"),
            actor_user_id=user.id,
        )
    )
    baseline = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    older_record = db.query(ModelCredential).filter(ModelCredential.id == older.id).one()
    newer_record = db.query(ModelCredential).filter(ModelCredential.id == newer.id).one()
    older_record.created_at = baseline
    older_record.updated_at = baseline
    newer_record.created_at = baseline + timedelta(minutes=1)
    newer_record.updated_at = baseline + timedelta(minutes=1)
    db.commit()

    asyncio.run(
        service.update_credential(
            async_db(db),
            older.id,
            CredentialUpdateDTO(display_name="最近更新"),
            actor_user_id=user.id,
        )
    )
    asyncio.run(
        service.verify_credential(
            async_db(db),
            older.id,
            actor_user_id=user.id,
        )
    )

    listed = asyncio.run(
        service.list_credentials(
            async_db(db),
            actor_user_id=user.id,
            owner_type="user",
        )
    )

    assert [item.id for item in listed] == [newer.id, older.id]


def test_system_pool_is_blocked_when_project_disallows(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()
    user = create_user(db)
    project = create_project(db, owner=user, allow_system_credential_pool=False)
    db.add(
        ModelCredential(
            owner_type="system",
            owner_id=None,
            provider="openai",
            api_dialect=OPENAI_DIALECT,
            display_name="系统",
            encrypted_key=crypto.encrypt("sk-system-1234"),
            default_model=OPENAI_MODEL,
        )
    )
    db.commit()
    service = create_credential_service(verifier=FakeVerifier(), crypto=crypto)

    with pytest.raises(NotFoundError):
        asyncio.run(
            service.resolve_active_credential(
                async_db(db),
                provider="openai",
                user_id=user.id,
                project_id=project.id,
            )
        )


def test_verify_credential_updates_timestamp_and_audits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )

    result = asyncio.run(
        service.verify_credential(
            async_db(db),
            credential.id,
            actor_user_id=user.id,
        )
    )

    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert result.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert result.probe_kind == "text_probe"
    assert stored.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert stored.stream_tool_verified_probe_kind is None
    assert stored.buffered_tool_verified_probe_kind is None
    assert audits[-1].details["status"] == "verified"
    assert audits[-1].details["probe_kind"] == "text_probe"


def test_verify_credential_accepts_explicit_tool_probe_kind(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(
        verifier=FakeVerifier(
            verified_at=verified_at,
            expected_probe_kind="tool_continuation_probe",
            expected_transport_mode="stream",
        )
    )
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )

    result = asyncio.run(
        service.verify_credential(
            async_db(db),
            credential.id,
            actor_user_id=user.id,
            probe_kind="tool_continuation_probe",
            transport_mode="stream",
        )
    )

    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert result.probe_kind == "tool_continuation_probe"
    assert result.transport_mode == "stream"
    assert result.message == "工具调用验证成功"
    assert result.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    assert stored.stream_tool_verified_probe_kind == "tool_continuation_probe"
    assert stored.stream_tool_last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert stored.buffered_tool_verified_probe_kind is None
    assert audits[-1].details["probe_kind"] == "tool_continuation_probe"
    assert audits[-1].details["transport_mode"] == "stream"


def test_verify_credential_keeps_stream_tool_verification_after_connection_recheck(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(
        verifier=FakeVerifier(
            verified_at=verified_at,
            expected_probe_kind="tool_continuation_probe",
            expected_transport_mode="stream",
        )
    )
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )
    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    stored.verified_probe_kind = "tool_continuation_probe"
    db.commit()

    asyncio.run(
        service.verify_credential(
            async_db(db),
            credential.id,
            actor_user_id=user.id,
            probe_kind="tool_continuation_probe",
            transport_mode="stream",
        )
    )

    service.verifier = FakeVerifier(
        verified_at=verified_at,
        expected_probe_kind="text_probe",
    )
    asyncio.run(
        service.verify_credential(
            async_db(db),
            credential.id,
            actor_user_id=user.id,
            probe_kind="text_probe",
        )
    )

    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    assert stored.verified_probe_kind is None
    assert stored.stream_tool_verified_probe_kind == "tool_continuation_probe"

def test_verify_credential_record_does_not_downgrade_stale_stream_tool_verification(
    db,
    engine,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(
        verifier=FakeVerifier(
            verified_at=verified_at,
            expected_probe_kind="text_probe",
        )
    )
    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )
    stale_credential = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()

    with Session(engine) as concurrent_db:
        concurrent_credential = concurrent_db.get(ModelCredential, created.id)
        assert concurrent_credential is not None
        concurrent_credential.stream_tool_verified_probe_kind = "tool_continuation_probe"
        concurrent_credential.stream_tool_last_verified_at = verified_at
        concurrent_db.commit()

    assert stale_credential.stream_tool_verified_probe_kind is None

    result = asyncio.run(
        verify_credential_record(
            async_db(db),
            credential=stale_credential,
            verifier=service.verifier,
            decrypt_api_key=service.crypto.decrypt,
            actor_user_id=user.id,
            event_type="credential_verify",
            audit_log_service=service.audit_log_service,
            probe_kind="text_probe",
            transport_mode=None,
        )
    )

    stored = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert result.probe_kind == "text_probe"
    assert stored.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert stored.stream_tool_verified_probe_kind == "tool_continuation_probe"
    assert audits[-1].details["stream_tool_verified_probe_kind"] == "tool_continuation_probe"

def test_verify_credential_failed_stream_tool_probe_clears_stale_stream_tool_verification(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )
    stored = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    stored.verified_probe_kind = "tool_continuation_probe"
    stored.last_verified_at = verified_at
    stored.stream_tool_verified_probe_kind = "tool_continuation_probe"
    stored.stream_tool_last_verified_at = verified_at
    stored.buffered_tool_verified_probe_kind = "tool_call_probe"
    stored.buffered_tool_last_verified_at = verified_at
    stored.last_verified_at = verified_at
    db.commit()

    with pytest.raises(BusinessRuleError, match="当前探测失败"):
        asyncio.run(
            verify_credential_record(
                async_db(db),
                credential=stored,
                verifier=FailingVerifier("当前探测失败"),
                decrypt_api_key=service.crypto.decrypt,
                actor_user_id=user.id,
                event_type="credential_verify",
                audit_log_service=service.audit_log_service,
                probe_kind="tool_continuation_probe",
                transport_mode="stream",
            )
        )

    refreshed = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert refreshed.verified_probe_kind is None
    assert refreshed.stream_tool_verified_probe_kind is None
    assert refreshed.stream_tool_last_verified_at is None
    assert refreshed.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert refreshed.buffered_tool_verified_probe_kind == "tool_call_probe"
    assert audits[-1].details["status"] == "failed"
    assert audits[-1].details["stream_tool_verified_probe_kind"] is None


def test_verify_credential_failed_higher_stream_probe_preserves_lower_stream_probe_kind(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )
    stored = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    stored.stream_tool_verified_probe_kind = "tool_definition_probe"
    stored.stream_tool_last_verified_at = verified_at
    db.commit()

    with pytest.raises(BusinessRuleError, match="当前探测失败"):
        asyncio.run(
            verify_credential_record(
                async_db(db),
                credential=stored,
                verifier=FailingVerifier("当前探测失败"),
                decrypt_api_key=service.crypto.decrypt,
                actor_user_id=user.id,
                event_type="credential_verify",
                audit_log_service=service.audit_log_service,
                probe_kind="tool_continuation_probe",
                transport_mode="stream",
            )
        )

    refreshed = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    assert refreshed.stream_tool_verified_probe_kind == "tool_definition_probe"
    assert refreshed.stream_tool_last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)


def test_verify_credential_failed_text_probe_clears_connection_and_tool_verification_state(
    db,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    created = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(display_name="OpenAI"),
            actor_user_id=user.id,
        )
    )
    stored = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    stored.verified_probe_kind = "tool_continuation_probe"
    stored.last_verified_at = verified_at
    stored.stream_tool_verified_probe_kind = "tool_continuation_probe"
    stored.stream_tool_last_verified_at = verified_at
    stored.buffered_tool_verified_probe_kind = "tool_call_probe"
    stored.buffered_tool_last_verified_at = verified_at
    db.commit()

    with pytest.raises(BusinessRuleError, match="当前探测失败"):
        asyncio.run(
            verify_credential_record(
                async_db(db),
                credential=stored,
                verifier=FailingVerifier("当前探测失败"),
                decrypt_api_key=service.crypto.decrypt,
                actor_user_id=user.id,
                event_type="credential_verify",
                audit_log_service=service.audit_log_service,
                probe_kind="text_probe",
                transport_mode=None,
            )
        )

    refreshed = db.query(ModelCredential).filter(ModelCredential.id == created.id).one()
    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert refreshed.last_verified_at is None
    assert refreshed.verified_probe_kind is None
    assert refreshed.stream_tool_verified_probe_kind is None
    assert refreshed.stream_tool_last_verified_at is None
    assert refreshed.buffered_tool_verified_probe_kind is None
    assert refreshed.buffered_tool_last_verified_at is None
    assert audits[-1].details["status"] == "failed"
    assert audits[-1].details["last_verified_at"] is None
    assert audits[-1].details["stream_tool_verified_probe_kind"] is None
    assert audits[-1].details["buffered_tool_verified_probe_kind"] is None


def test_update_and_disable_credential(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = asyncio.run(
        service.create_credential(
            async_db(db),
            _create_payload(
                provider="deepseek",
                display_name="旧名字",
                default_model="deepseek-chat",
            ),
            actor_user_id=user.id,
        )
    )

    updated = asyncio.run(
        service.update_credential(
            async_db(db),
            credential.id,
            CredentialUpdateDTO(
                display_name="新名字",
                api_key="sk-updated-5678",
                default_model="deepseek-chat-v2",
            ),
            actor_user_id=user.id,
        )
    )
    disabled = asyncio.run(
        service.disable_credential(
            async_db(db),
            credential.id,
            actor_user_id=user.id,
        )
    )

    assert updated.display_name == "新名字"
    assert updated.default_model == "deepseek-chat-v2"
    assert updated.masked_key == "sk-...5678"
    assert disabled.is_active is False


def test_resolve_active_credential_model_falls_back_to_default_model(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()
    user = create_user(db)
    db.add(
        ModelCredential(
            owner_type="user",
            owner_id=user.id,
            provider="openai",
            api_dialect=OPENAI_DIALECT,
            display_name="OpenAI",
            encrypted_key=crypto.encrypt("sk-user-1234"),
            default_model=OPENAI_MODEL,
            is_active=True,
        )
    )
    db.commit()
    service = create_credential_service(verifier=FakeVerifier(), crypto=crypto)

    resolved = asyncio.run(
        service.resolve_active_credential_model(
            async_db(db),
            provider="openai",
            requested_model_name=None,
            user_id=user.id,
        )
    )

    assert resolved.model_name == OPENAI_MODEL
