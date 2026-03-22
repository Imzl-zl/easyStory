from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.main import create_app
from app.modules.credential.models import ModelCredential
from app.modules.observability.models import AuditLog
from app.modules.project.models import Project
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_user


async def test_credential_audit_log_api_lists_user_and_soft_deleted_project_logs(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-audit-log-api")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        seeded = _seed_credential_audit_graph(session_factory, soft_delete_project=True)

        async with started_async_client(app) as client:
            user_logs_response = await client.get(
                f"/api/v1/credentials/{seeded['user_credential_id']}/audit-logs",
                params={"event_type": "credential_disable"},
                headers=_auth_headers(seeded["owner_id"]),
            )
            assert user_logs_response.status_code == 200
            user_logs = user_logs_response.json()
            assert [item["event_type"] for item in user_logs] == ["credential_disable"]
            assert user_logs[0]["details"]["owner_type"] == "user"

            project_logs_response = await client.get(
                f"/api/v1/credentials/{seeded['project_credential_id']}/audit-logs",
                headers=_auth_headers(seeded["owner_id"]),
            )
            assert project_logs_response.status_code == 200
            project_logs = project_logs_response.json()
            assert [item["event_type"] for item in project_logs] == [
                "credential_verify",
                "credential_create",
            ]
            assert project_logs[0]["details"]["owner_type"] == "project"
            assert project_logs[0]["details"]["status"] == "verified"

            blank_filter_response = await client.get(
                f"/api/v1/credentials/{seeded['project_credential_id']}/audit-logs",
                params={"event_type": "   "},
                headers=_auth_headers(seeded["owner_id"]),
            )
            assert blank_filter_response.status_code == 422
            assert blank_filter_response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_credential_audit_log_api_hides_foreign_and_system_credentials(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-audit-log-api-scope")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        seeded = _seed_credential_audit_graph(session_factory, soft_delete_project=False)

        async with started_async_client(app) as client:
            foreign_response = await client.get(
                f"/api/v1/credentials/{seeded['user_credential_id']}/audit-logs",
                headers=_auth_headers(seeded["outsider_id"]),
            )
            assert foreign_response.status_code == 404
            assert foreign_response.json()["code"] == "not_found"

            system_response = await client.get(
                f"/api/v1/credentials/{seeded['system_credential_id']}/audit-logs",
                headers=_auth_headers(seeded["owner_id"]),
            )
            assert system_response.status_code == 404
            assert system_response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_credential_audit_graph(
    session_factory,
    *,
    soft_delete_project: bool,
) -> dict[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        outsider = create_user(session)
        project = Project(name="Credential Audit API", owner_id=owner.id)
        session.add(project)
        session.commit()
        session.refresh(project)

        user_credential = _create_credential(
            session,
            owner_type="user",
            owner_id=owner.id,
            provider="openai",
        )
        project_credential = _create_credential(
            session,
            owner_type="project",
            owner_id=project.id,
            provider="deepseek",
        )
        system_credential = _create_credential(
            session,
            owner_type="system",
            owner_id=None,
            provider="anthropic",
        )
        _create_credential_audit_log(
            session,
            actor_user_id=owner.id,
            credential=user_credential,
            event_type="credential_create",
        )
        _create_credential_audit_log(
            session,
            actor_user_id=owner.id,
            credential=user_credential,
            event_type="credential_disable",
        )
        _create_credential_audit_log(
            session,
            actor_user_id=owner.id,
            credential=project_credential,
            event_type="credential_create",
        )
        _create_credential_audit_log(
            session,
            actor_user_id=owner.id,
            credential=project_credential,
            event_type="credential_verify",
            extra_details={"status": "verified"},
        )
        if soft_delete_project:
            project.deleted_at = datetime.now(timezone.utc)
            session.add(project)
            session.commit()
        return {
            "owner_id": owner.id,
            "outsider_id": outsider.id,
            "user_credential_id": user_credential.id,
            "project_credential_id": project_credential.id,
            "system_credential_id": system_credential.id,
        }


def _create_credential(
    session,
    *,
    owner_type: str,
    owner_id: uuid.UUID | None,
    provider: str,
) -> ModelCredential:
    credential = ModelCredential(
        owner_type=owner_type,
        owner_id=owner_id,
        provider=provider,
        display_name=f"{owner_type}-{provider}",
        encrypted_key=f"ciphertext-{provider}",
        is_active=True,
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)
    return credential


def _create_credential_audit_log(
    session,
    *,
    actor_user_id: uuid.UUID,
    credential: ModelCredential,
    event_type: str,
    extra_details: dict | None = None,
) -> None:
    details = {
        "provider": credential.provider,
        "owner_type": credential.owner_type,
        "owner_id": str(credential.owner_id) if credential.owner_id is not None else None,
    }
    if extra_details is not None:
        details.update(extra_details)
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type="model_credential",
            entity_id=credential.id,
            details=details,
        )
    )
    session.commit()
