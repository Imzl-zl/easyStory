from __future__ import annotations

import pytest

from app.modules.observability.service import create_audit_log_query_service
from app.modules.project.service import create_project_deletion_service
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user


async def test_project_audit_log_query_service_lists_deleted_and_restored_project_logs(
    tmp_path,
) -> None:
    query_service = create_audit_log_query_service()
    deletion_service = create_project_deletion_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-audit-log-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with async_session_factory() as session:
            await deletion_service.soft_delete_project(
                session,
                project_id,
                owner_id=owner_id,
            )

        async with async_session_factory() as session:
            deleted_logs = await query_service.list_project_audit_logs(
                session,
                project_id,
                owner_id=owner_id,
            )

        async with async_session_factory() as session:
            await deletion_service.restore_project(
                session,
                project_id,
                owner_id=owner_id,
            )

        async with async_session_factory() as session:
            restored_logs = await query_service.list_project_audit_logs(
                session,
                project_id,
                owner_id=owner_id,
                event_type=" project_restore ",
            )

        assert [item.event_type for item in deleted_logs] == ["project_delete"]
        assert deleted_logs[0].entity_type == "project"
        assert deleted_logs[0].details is not None
        assert deleted_logs[0].details["owner_id"] == str(owner_id)
        assert deleted_logs[0].details["deleted_at"] is not None
        assert [item.event_type for item in restored_logs] == ["project_restore"]
        assert restored_logs[0].details is not None
        assert restored_logs[0].details["deleted_at"] is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_audit_log_query_service_rejects_blank_filter_and_foreign_owner(
    tmp_path,
) -> None:
    query_service = create_audit_log_query_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-audit-log-service-owner")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            owner_id = owner.id
            outsider_id = outsider.id

        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="event_type filter cannot be blank"):
                await query_service.list_project_audit_logs(
                    session,
                    project_id,
                    owner_id=owner_id,
                    event_type="   ",
                )

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError, match="Project not found"):
                await query_service.list_project_audit_logs(
                    session,
                    project_id,
                    owner_id=outsider_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
