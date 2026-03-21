from __future__ import annotations

import copy
import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.modules.export.models import Export
from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import (
    TEST_JWT_SECRET,
    NoopWorkflowDispatcher as _NoopDispatcher,
    auth_headers as _auth_headers,
    build_runtime_app as _build_runtime_app,
    seed_workflow_project as _seed_project,
)
from tests.unit.models.helpers import (
    create_workflow,
)
DEFAULT_WORKFLOW_SNAPSHOT = {
    "id": "workflow.xuanhuan_manual",
    "name": "玄幻小说手动创作",
    "version": "1.0.0",
    "mode": "manual",
    "nodes": [
        {
            "id": "chapter_split",
            "name": "拆分章节任务",
            "type": "generate",
            "depends_on": ["outline", "opening_plan"],
        }
    ],
}


async def test_start_workflow_creates_running_execution_with_snapshots(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-start")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    app = _build_runtime_app(session_factory, async_session_factory)

    try:
        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "paused"
        assert body["workflow_id"] == "workflow.xuanhuan_manual"
        assert body["current_node_id"] == "chapter_split"
        assert body["current_node_name"] == "拆分章节任务"
        assert body["resume_from_node"] == "chapter_gen"

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(body["execution_id"]))
            assert workflow is not None
            assert workflow.workflow_snapshot["id"] == "workflow.xuanhuan_manual"
            assert "hook.auto_save" in workflow.workflow_snapshot["resolved_hooks"]
            assert "skill.review.style" in workflow.skills_snapshot
            assert "agent.style_checker" in workflow.agents_snapshot
            tasks = (
                session.query(ChapterTask)
                .filter(ChapterTask.workflow_execution_id == workflow.id)
                .order_by(ChapterTask.chapter_number.asc())
                .all()
            )
            assert [task.chapter_number for task in tasks] == [1, 2]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_start_workflow_route_uses_dispatcher_and_returns_before_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-dispatcher")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    dispatcher = _NoopDispatcher()
    app = _build_runtime_app(
        session_factory,
        async_session_factory,
        runtime_dispatcher=dispatcher,
    )

    try:
        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "running"
        assert dispatcher.calls == [(uuid.UUID(body["execution_id"]), owner_id)]

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(body["execution_id"]))
            assert workflow is not None
            assert workflow.status == "running"
            assert workflow.current_node_id == "chapter_split"
            assert session.query(ChapterTask).count() == 0
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_start_workflow_requires_confirmed_preparation_assets(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-assets")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=False)
    app = _build_runtime_app(session_factory, async_session_factory)

    try:
        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
        assert "大纲必须先确认后才能启动工作流" in response.json()["detail"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_start_workflow_rejects_when_project_has_active_execution(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-active")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    _seed_active_workflow(session_factory, project_id)
    app = _build_runtime_app(session_factory, async_session_factory)

    try:
        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 409
        assert response.json()["code"] == "conflict"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_workflow_detail_pause_resume_and_cancel_flow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-flow")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    app = _build_runtime_app(session_factory, async_session_factory)
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )
            execution_id = start_response.json()["execution_id"]

            detail_response = await client.get(
                f"/api/v1/workflows/{execution_id}",
                headers=headers,
            )
            assert detail_response.status_code == 200
            assert detail_response.json()["current_node_id"] == "chapter_split"

            pause_response = await client.post(
                f"/api/v1/workflows/{execution_id}/pause",
                json={"reason": "user_request"},
                headers=headers,
            )
            assert pause_response.status_code == 200
            assert pause_response.json()["status"] == "paused"
            assert pause_response.json()["pause_reason"] is None
            assert pause_response.json()["resume_from_node"] == "chapter_gen"
            assert pause_response.json()["has_runtime_snapshot"] is True

            resume_response = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert resume_response.status_code == 200
            assert resume_response.json()["status"] == "paused"
            assert resume_response.json()["current_node_id"] == "chapter_gen"
            assert resume_response.json()["resume_from_node"] == "chapter_gen"

            cancel_response = await client.post(
                f"/api/v1/workflows/{execution_id}/cancel",
                headers=headers,
            )
            assert cancel_response.status_code == 200
            assert cancel_response.json()["status"] == "cancelled"
            assert cancel_response.json()["completed_at"] is not None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_resume_workflow_blocks_when_chapter_tasks_are_stale(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-stale")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    app = _build_runtime_app(session_factory, async_session_factory)
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )
            execution_id = start_response.json()["execution_id"]
            pause_response = await client.post(
                f"/api/v1/workflows/{execution_id}/pause",
                headers=headers,
            )
            assert pause_response.status_code == 200

            _seed_stale_chapter_task(session_factory, execution_id)

            resume_response = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert resume_response.status_code == 422
            assert resume_response.json()["code"] == "business_rule_error"
            assert "chapter_split" in resume_response.json()["detail"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_resume_workflow_waiting_confirmation_keeps_existing_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-waiting")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    app = _build_runtime_app(session_factory, async_session_factory)
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )
            execution_id = start_response.json()["execution_id"]

            first_resume = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert first_resume.status_code == 200
            assert first_resume.json()["status"] == "paused"

            with session_factory() as session:
                workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
                assert workflow is not None
                original_snapshot = copy.deepcopy(workflow.snapshot)
                assert original_snapshot["pending_actions"][0]["type"] == "chapter_confirmation"
                assert workflow.pause_reason is None

            second_resume = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert second_resume.status_code == 422
            assert second_resume.json()["code"] == "business_rule_error"
            assert "待确认" in second_resume.json()["detail"]

            with session_factory() as session:
                workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
                assert workflow is not None
                assert workflow.snapshot == original_snapshot
                assert workflow.pause_reason is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_workflow_runtime_reaches_export_after_chapter_approvals(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-api-export")
    )
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    export_root = Path.cwd() / ".pytest-exports" / f"workflow-runtime-{uuid.uuid4().hex}"
    app = _build_runtime_app(
        session_factory,
        async_session_factory,
        export_root=export_root,
    )
    headers = _auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )
            execution_id = start_response.json()["execution_id"]

            resume_first = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert resume_first.status_code == 200
            assert resume_first.json()["status"] == "paused"
            assert resume_first.json()["current_node_id"] == "chapter_gen"

            approve_first = await client.post(
                f"/api/v1/projects/{project_id}/chapters/1/approve",
                headers=headers,
            )
            assert approve_first.status_code == 200

            resume_second = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert resume_second.status_code == 200
            assert resume_second.json()["status"] == "paused"

            approve_second = await client.post(
                f"/api/v1/projects/{project_id}/chapters/2/approve",
                headers=headers,
            )
            assert approve_second.status_code == 200

            finish_response = await client.post(
                f"/api/v1/workflows/{execution_id}/resume",
                headers=headers,
            )
            assert finish_response.status_code == 200
            assert finish_response.json()["status"] == "completed"

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
            assert workflow is not None
            tasks = (
                session.query(ChapterTask)
                .filter(ChapterTask.workflow_execution_id == workflow.id)
                .order_by(ChapterTask.chapter_number.asc())
                .all()
            )
            exports = (
                session.query(Export)
                .filter(Export.project_id == workflow.project_id)
                .order_by(Export.format.asc())
                .all()
            )
            assert [task.status for task in tasks] == ["completed", "completed"]
            assert [item.format for item in exports] == ["markdown", "txt"]
            for item in exports:
                file_path = export_root / Path(item.file_path)
                assert not Path(item.file_path).is_absolute()
                assert file_path.exists()
                assert file_path.read_text(encoding="utf-8")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
        shutil.rmtree(export_root, ignore_errors=True)
def _seed_active_workflow(
    session_factory: sessionmaker[Session],
    project_id: str,
) -> None:
    with session_factory() as session:
        project = session.get(Project, uuid.UUID(project_id))
        assert project is not None
        create_workflow(
            session,
            project=project,
            template_id=project.template_id,
            status="running",
            workflow_snapshot=DEFAULT_WORKFLOW_SNAPSHOT,
        )


def _seed_stale_chapter_task(
    session_factory: sessionmaker[Session],
    execution_id: str,
) -> None:
    with session_factory() as session:
        chapter_task = (
            session.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == uuid.UUID(execution_id))
            .filter(ChapterTask.chapter_number == 1)
            .one_or_none()
        )
        assert chapter_task is not None
        chapter_task.status = "stale"
        session.commit()
