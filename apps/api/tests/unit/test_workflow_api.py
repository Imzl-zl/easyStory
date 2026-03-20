from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.db import Base
from tests.unit.models.helpers import (
    create_project,
    create_template,
    create_user,
    create_workflow,
    ready_project_setting,
)

TEST_JWT_SECRET = "test-jwt-secret"
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


def test_start_workflow_creates_running_execution_with_snapshots(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "running"
        assert body["workflow_id"] == "workflow.xuanhuan_manual"
        assert body["current_node_id"] == "chapter_split"
        assert body["current_node_name"] == "拆分章节任务"

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(body["execution_id"]))
            assert workflow is not None
            assert workflow.workflow_snapshot["id"] == "workflow.xuanhuan_manual"
            assert "hook.auto_save" in workflow.workflow_snapshot["resolved_hooks"]
            assert "skill.review.style" in workflow.skills_snapshot
            assert "agent.style_checker" in workflow.agents_snapshot
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_start_workflow_requires_confirmed_preparation_assets(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=False)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
        assert "大纲必须先确认后才能启动工作流" in response.json()["detail"]
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_start_workflow_rejects_when_project_has_active_execution(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    _seed_active_workflow(session_factory, project_id)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 409
        assert response.json()["code"] == "conflict"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_workflow_detail_pause_resume_and_cancel_flow(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = TestClient(create_app(session_factory=session_factory))
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        detail_response = client.get(f"/api/v1/workflows/{execution_id}", headers=headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["current_node_id"] == "chapter_split"

        pause_response = client.post(
            f"/api/v1/workflows/{execution_id}/pause",
            json={"reason": "user_request"},
            headers=headers,
        )
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "paused"
        assert pause_response.json()["pause_reason"] == "user_request"
        assert pause_response.json()["resume_from_node"] == "chapter_split"
        assert pause_response.json()["has_runtime_snapshot"] is True

        resume_response = client.post(
            f"/api/v1/workflows/{execution_id}/resume",
            headers=headers,
        )
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "running"
        assert resume_response.json()["pause_reason"] is None

        cancel_response = client.post(
            f"/api/v1/workflows/{execution_id}/cancel",
            headers=headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
        assert cancel_response.json()["completed_at"] is not None
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_resume_workflow_blocks_when_chapter_tasks_are_stale(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = TestClient(create_app(session_factory=session_factory))
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]
        pause_response = client.post(
            f"/api/v1/workflows/{execution_id}/pause",
            headers=headers,
        )
        assert pause_response.status_code == 200

        _seed_stale_chapter_task(session_factory, execution_id)

        resume_response = client.post(
            f"/api/v1/workflows/{execution_id}/resume",
            headers=headers,
        )
        assert resume_response.status_code == 422
        assert resume_response.json()["code"] == "business_rule_error"
        assert "chapter_split" in resume_response.json()["detail"]
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def _build_session_factory() -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(engine, expire_on_commit=False, class_=Session)
    return session_factory, engine


def _seed_project(
    session_factory: sessionmaker[Session],
    *,
    ready_assets: bool,
) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        template = create_template(session)
        project = create_project(
            session,
            owner=owner,
            template_id=template.id,
            project_setting=ready_project_setting(),
        )
        if ready_assets:
            _create_asset(session, project.id, "outline", "大纲")
            _create_asset(session, project.id, "opening_plan", "开篇设计")
        return str(project.id), owner.id


def _create_asset(
    session: Session,
    project_id: uuid.UUID,
    content_type: str,
    title: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        status="approved",
    )
    session.add(content)
    session.flush()
    session.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=f"{title}内容",
        )
    )
    session.commit()


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
        workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
        assert workflow is not None
        session.add(
            ChapterTask(
                project_id=workflow.project_id,
                workflow_execution_id=workflow.id,
                chapter_number=1,
                title="第一章",
                brief="章节任务",
                status="stale",
            )
        )
        session.commit()


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
