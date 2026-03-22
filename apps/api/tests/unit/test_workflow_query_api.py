from __future__ import annotations

from datetime import UTC, datetime, timedelta
import uuid

from app.modules.project.models import Project
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import (
    TEST_JWT_SECRET,
    auth_headers as _auth_headers,
    build_runtime_app as _build_runtime_app,
    seed_workflow_project as _seed_project,
)
from tests.unit.models.helpers import create_user, create_workflow

WORKFLOW_SNAPSHOT = {
    "id": "workflow.xuanhuan_manual",
    "name": "玄幻小说手动创作",
    "version": "1.0.0",
    "mode": "manual",
    "nodes": [
        {
            "id": "chapter_gen",
            "name": "生成章节",
            "type": "generate",
            "depends_on": ["chapter_split"],
        }
    ],
}
WORKFLOW_QUERY_BASE_TIME = datetime(2026, 3, 22, 17, 0, tzinfo=UTC)


async def test_project_workflow_list_api_returns_history_and_supports_status_filter(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-query-api")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    _seed_workflows(session_factory, project_id)
    app = _build_runtime_app(session_factory, async_session_factory)

    try:
        async with started_async_client(app) as client:
            all_response = await client.get(
                f"/api/v1/projects/{project_id}/workflows",
                headers=_auth_headers(owner_id),
            )
            filtered_response = await client.get(
                f"/api/v1/projects/{project_id}/workflows",
                params={"status": "running"},
                headers=_auth_headers(owner_id),
            )

        assert all_response.status_code == 200
        payload = all_response.json()
        assert [item["status"] for item in payload] == ["completed", "running"]
        assert payload[0]["workflow_id"] == "workflow.xuanhuan_manual"
        assert payload[0]["current_node_name"] == "生成章节"
        assert filtered_response.status_code == 200
        assert [item["status"] for item in filtered_response.json()] == ["running"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_workflow_list_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-query-api-owner")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    _seed_workflows(session_factory, project_id)
    app = _build_runtime_app(session_factory, async_session_factory)

    try:
        with session_factory() as session:
            outsider_id = create_user(session).id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/workflows",
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_workflows(session_factory, project_id: str) -> None:
    with session_factory() as session:
        project = session.get(Project, uuid.UUID(project_id))
        assert project is not None
        create_workflow(
            session,
            project=project,
            template_id=project.template_id,
            status="running",
            current_node_id="chapter_gen",
            workflow_snapshot=WORKFLOW_SNAPSHOT,
            created_at=WORKFLOW_QUERY_BASE_TIME,
            updated_at=WORKFLOW_QUERY_BASE_TIME,
            started_at=WORKFLOW_QUERY_BASE_TIME,
        )
        create_workflow(
            session,
            project=project,
            template_id=project.template_id,
            status="completed",
            current_node_id="chapter_gen",
            workflow_snapshot=WORKFLOW_SNAPSHOT,
            created_at=WORKFLOW_QUERY_BASE_TIME + timedelta(minutes=1),
            updated_at=WORKFLOW_QUERY_BASE_TIME + timedelta(minutes=4),
            started_at=WORKFLOW_QUERY_BASE_TIME + timedelta(minutes=1),
            completed_at=WORKFLOW_QUERY_BASE_TIME + timedelta(minutes=4),
        )
