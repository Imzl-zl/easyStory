from __future__ import annotations

from app.main import create_app
from app.modules.content.models import Content, ContentVersion
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import (
    create_chapter_task,
    create_project,
    create_template,
    create_user,
    create_workflow,
    ready_project_setting,
)


async def test_preparation_status_api_reports_outline_gate_for_new_project(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="preparation-status-api-new-project")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            template = create_template(session)
            owner_id = owner.id
            template_id = template.id

        async with started_async_client(app) as client:
            create_response = await client.post(
                "/api/v1/projects",
                json={
                    "name": "状态项目",
                    "template_id": str(template_id),
                    "project_setting": ready_project_setting(),
                },
                headers=_auth_headers(owner_id),
            )
            assert create_response.status_code == 200
            project_id = create_response.json()["id"]

            status_response = await client.get(
                f"/api/v1/projects/{project_id}/preparation/status",
                headers=_auth_headers(owner_id),
            )

        assert status_response.status_code == 200
        body = status_response.json()
        assert body["outline"]["step_status"] == "not_started"
        assert body["outline"]["content_status"] == "draft"
        assert body["opening_plan"]["step_status"] == "not_started"
        assert body["chapter_tasks"]["step_status"] == "not_started"
        assert body["can_start_workflow"] is False
        assert body["next_step"] == "outline"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_preparation_status_api_reports_stale_chapter_task_gate(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="preparation-status-api-stale-task")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(
                session,
                owner=owner,
                project_setting=ready_project_setting(),
            )
            workflow = create_workflow(
                session,
                project=project,
                status="paused",
                current_node_id="chapter_gen",
            )
            _create_story_asset(session, project.id, "outline", "approved", "主线大纲")
            _create_story_asset(session, project.id, "opening_plan", "approved", "前三章开篇设计")
            create_chapter_task(
                session,
                workflow=workflow,
                chapter_number=1,
                title="第一章",
                brief="旧任务",
                status="stale",
            )
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/preparation/status",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["outline"]["step_status"] == "approved"
        assert body["opening_plan"]["step_status"] == "approved"
        assert body["chapter_tasks"]["step_status"] == "stale"
        assert body["chapter_tasks"]["counts"]["stale"] == 1
        assert body["active_workflow"]["status"] == "paused"
        assert body["can_start_workflow"] is False
        assert body["next_step"] == "chapter_tasks"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_preparation_status_api_hides_other_users_project(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="preparation-status-api-owner")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(
                session,
                owner=owner,
                project_setting=ready_project_setting(),
            )
            project_id = project.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/preparation/status",
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _create_story_asset(session, project_id, content_type: str, status: str, content_text: str) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title="大纲" if content_type == "outline" else "开篇设计",
        chapter_number=None,
        status=status,
    )
    session.add(content)
    session.flush()
    session.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=content_text,
            is_current=True,
        )
    )
    session.commit()
