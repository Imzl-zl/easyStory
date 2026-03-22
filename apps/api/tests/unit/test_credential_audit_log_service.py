from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from app.modules.credential.models import ModelCredential
from app.modules.observability.models import AuditLog
from app.modules.observability.service import create_audit_log_query_service
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user


async def test_credential_audit_log_query_service_lists_user_and_soft_deleted_project_logs(
    tmp_path,
) -> None:
    query_service = create_audit_log_query_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-audit-log-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
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
            project.deleted_at = datetime.now(timezone.utc)
            session.add(project)
            session.commit()
            owner_id = owner.id
            user_credential_id = user_credential.id
            project_credential_id = project_credential.id

        async with async_session_factory() as session:
            user_logs = await query_service.list_credential_audit_logs(
                session,
                user_credential_id,
                owner_id=owner_id,
                event_type=" credential_disable ",
            )

        async with async_session_factory() as session:
            project_logs = await query_service.list_credential_audit_logs(
                session,
                project_credential_id,
                owner_id=owner_id,
            )

        assert [item.event_type for item in user_logs] == ["credential_disable"]
        assert user_logs[0].details is not None
        assert user_logs[0].details["owner_type"] == "user"
        assert [item.event_type for item in project_logs] == [
            "credential_verify",
            "credential_create",
        ]
        assert project_logs[0].details is not None
        assert project_logs[0].details["owner_type"] == "project"
        assert project_logs[0].details["status"] == "verified"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_credential_audit_log_query_service_rejects_blank_filter_and_hidden_scopes(
    tmp_path,
) -> None:
    query_service = create_audit_log_query_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="credential-audit-log-service-scope")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            create_project(session, owner=owner)
            user_credential = _create_credential(
                session,
                owner_type="user",
                owner_id=owner.id,
                provider="openai",
            )
            system_credential = _create_credential(
                session,
                owner_type="system",
                owner_id=None,
                provider="anthropic",
            )
            owner_id = owner.id
            outsider_id = outsider.id
            user_credential_id = user_credential.id
            system_credential_id = system_credential.id

        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="event_type filter cannot be blank"):
                await query_service.list_credential_audit_logs(
                    session,
                    user_credential_id,
                    owner_id=owner_id,
                    event_type="   ",
                )

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError, match="Credential not found"):
                await query_service.list_credential_audit_logs(
                    session,
                    user_credential_id,
                    owner_id=outsider_id,
                )

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError, match="Credential not found"):
                await query_service.list_credential_audit_logs(
                    session,
                    system_credential_id,
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


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
