from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user


async def test_project_audit_log_api_lists_deleted_and_restored_project_logs(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-audit-log-api")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            owner_id = owner.id
            project_id = project.id

        async with started_async_client(app) as client:
            delete_response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=_auth_headers(owner_id),
            )
            assert delete_response.status_code == 200

            deleted_logs_response = await client.get(
                f"/api/v1/projects/{project_id}/audit-logs",
                headers=_auth_headers(owner_id),
            )
            assert deleted_logs_response.status_code == 200
            deleted_logs = deleted_logs_response.json()
            assert [item["event_type"] for item in deleted_logs] == ["project_delete"]
            assert deleted_logs[0]["entity_type"] == "project"
            assert deleted_logs[0]["details"]["deleted_at"] is not None

            restore_response = await client.post(
                f"/api/v1/projects/{project_id}/restore",
                headers=_auth_headers(owner_id),
            )
            assert restore_response.status_code == 200

            restored_logs_response = await client.get(
                f"/api/v1/projects/{project_id}/audit-logs",
                params={"event_type": "project_restore"},
                headers=_auth_headers(owner_id),
            )
            assert restored_logs_response.status_code == 200
            restored_logs = restored_logs_response.json()
            assert [item["event_type"] for item in restored_logs] == ["project_restore"]
            assert restored_logs[0]["details"]["deleted_at"] is None

            blank_filter_response = await client.get(
                f"/api/v1/projects/{project_id}/audit-logs",
                params={"event_type": "   "},
                headers=_auth_headers(owner_id),
            )
            assert blank_filter_response.status_code == 422
            assert blank_filter_response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_audit_log_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-audit-log-api-owner")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/audit-logs",
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
