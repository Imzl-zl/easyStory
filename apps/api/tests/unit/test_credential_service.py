from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.credential.infrastructure import (
    CredentialCrypto,
    CredentialVerificationResult,
)
from app.modules.credential.models import ModelCredential
from app.modules.credential.service import (
    CredentialCreateDTO,
    CredentialUpdateDTO,
    create_credential_service,
)
from app.modules.observability.models import AuditLog
from app.shared.runtime.errors import ConflictError, NotFoundError
from tests.unit.models.helpers import create_project, create_user

TEST_MASTER_KEY = "credential-master-key-for-tests"


class FakeVerifier:
    def __init__(self, verified_at: datetime | None = None) -> None:
        self.verified_at = verified_at or datetime.now(timezone.utc)

    def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
    ) -> CredentialVerificationResult:
        assert provider
        assert api_key
        return CredentialVerificationResult(
            verified_at=self.verified_at,
            message="Credential verified",
        )


def test_credential_crypto_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    crypto = CredentialCrypto()

    encrypted = crypto.encrypt("sk-secret-1234")

    assert encrypted != "sk-secret-1234"
    assert crypto.decrypt(encrypted) == "sk-secret-1234"


def test_create_user_credential_encrypts_and_audits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())

    result = service.create_credential(
        db,
        CredentialCreateDTO(
            owner_type="user",
            provider="OpenAI",
            display_name="我的 OpenAI Key",
            api_key="sk-secret-1234",
        ),
        actor_user_id=user.id,
    )

    stored = db.query(ModelCredential).filter(ModelCredential.id == result.id).one()
    audits = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()

    assert stored.encrypted_key != "sk-secret-1234"
    assert result.provider == "openai"
    assert result.masked_key == "sk-...1234"
    assert audits[-1].event_type == "credential_create"


def test_create_duplicate_provider_in_same_scope_conflicts(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    payload = CredentialCreateDTO(
        owner_type="user",
        provider="openai",
        display_name="OpenAI",
        api_key="sk-first-1234",
    )
    service.create_credential(db, payload, actor_user_id=user.id)

    with pytest.raises(ConflictError):
        service.create_credential(db, payload, actor_user_id=user.id)


def test_project_credential_requires_owned_project(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = create_credential_service(verifier=FakeVerifier())

    with pytest.raises(NotFoundError):
        service.create_credential(
            db,
            CredentialCreateDTO(
                owner_type="project",
                project_id=project.id,
                provider="openai",
                display_name="项目 Key",
                api_key="sk-secret-1234",
            ),
            actor_user_id=outsider.id,
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
        display_name="系统",
        encrypted_key=crypto.encrypt("sk-system-1234"),
    )
    user_credential = ModelCredential(
        owner_type="user",
        owner_id=user.id,
        provider="openai",
        display_name="用户",
        encrypted_key=crypto.encrypt("sk-user-1234"),
    )
    project_credential = ModelCredential(
        owner_type="project",
        owner_id=project.id,
        provider="openai",
        display_name="项目",
        encrypted_key=crypto.encrypt("sk-project-1234"),
    )
    db.add_all([system_credential, user_credential, project_credential])
    db.commit()

    resolved = service.resolve_active_credential(
        db,
        provider="openai",
        user_id=user.id,
        project_id=project.id,
    )

    assert resolved.id == project_credential.id
    db.delete(project_credential)
    db.commit()

    resolved = service.resolve_active_credential(
        db,
        provider="openai",
        user_id=user.id,
        project_id=project.id,
    )
    assert resolved.id == user_credential.id
    db.delete(user_credential)
    db.commit()

    resolved = service.resolve_active_credential(
        db,
        provider="openai",
        user_id=user.id,
        project_id=project.id,
    )
    assert resolved.id == system_credential.id


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
            display_name="系统",
            encrypted_key=crypto.encrypt("sk-system-1234"),
        )
    )
    db.commit()
    service = create_credential_service(verifier=FakeVerifier(), crypto=crypto)

    with pytest.raises(NotFoundError):
        service.resolve_active_credential(
            db,
            provider="openai",
            user_id=user.id,
            project_id=project.id,
        )


def test_verify_credential_updates_timestamp_and_audits(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    verified_at = datetime.now(timezone.utc).replace(microsecond=0)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier(verified_at=verified_at))
    credential = service.create_credential(
        db,
        CredentialCreateDTO(
            owner_type="user",
            provider="openai",
            display_name="OpenAI",
            api_key="sk-secret-1234",
        ),
        actor_user_id=user.id,
    )

    result = service.verify_credential(db, credential.id, actor_user_id=user.id)

    stored = db.query(ModelCredential).filter(ModelCredential.id == credential.id).one()
    audits = db.query(AuditLog).filter(AuditLog.event_type == "credential_verify").all()
    assert result.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert stored.last_verified_at.replace(tzinfo=None) == verified_at.replace(tzinfo=None)
    assert audits[-1].details["status"] == "verified"


def test_update_and_disable_credential(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    user = create_user(db)
    service = create_credential_service(verifier=FakeVerifier())
    credential = service.create_credential(
        db,
        CredentialCreateDTO(
            owner_type="user",
            provider="deepseek",
            display_name="旧名字",
            api_key="sk-secret-1234",
        ),
        actor_user_id=user.id,
    )

    updated = service.update_credential(
        db,
        credential.id,
        CredentialUpdateDTO(display_name="新名字", api_key="sk-updated-5678"),
        actor_user_id=user.id,
    )
    disabled = service.disable_credential(db, credential.id, actor_user_id=user.id)

    assert updated.display_name == "新名字"
    assert updated.masked_key == "sk-...5678"
    assert disabled.is_active is False
