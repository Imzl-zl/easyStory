from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.content.models import Content, ContentVersion
from app.modules.user.service import TokenService
from app.modules.workflow.models import WorkflowExecution
from app.shared.db import Base
from tests.unit.models.helpers import (
    create_chapter_task,
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
        {"id": "outline", "name": "生成大纲", "type": "generate", "depends_on": []},
        {
            "id": "opening_plan",
            "name": "生成开篇设计",
            "type": "generate",
            "depends_on": ["outline"],
        },
        {
            "id": "chapter_split",
            "name": "拆分章节任务",
            "type": "generate",
            "depends_on": ["outline", "opening_plan"],
        },
        {
            "id": "chapter_gen",
            "name": "生成章节",
            "type": "generate",
            "depends_on": ["chapter_split"],
        },
    ],
}


def test_regenerate_chapter_tasks_replaces_active_workflow_plan(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id, workflow_id = _seed_project_with_active_workflow(
        session_factory,
        ready_assets=True,
    )
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/chapter-tasks/regenerate",
            json={
                "chapters": [
                    {
                        "chapter_number": 1,
                        "title": "第一章 逃亡夜",
                        "brief": "主角连夜出逃并暴露追兵",
                        "key_characters": ["林渊", "执法长老"],
                        "key_events": ["夜逃", "追捕"],
                    },
                    {
                        "chapter_number": 2,
                        "title": "第二章 山门截杀",
                        "brief": "主角在山门外首次反杀",
                        "key_characters": ["林渊"],
                        "key_events": ["伏击", "反杀"],
                    },
                ]
            },
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["workflow_execution_id"] == workflow_id
        assert body["current_node_id"] == "chapter_gen"
        assert [item["chapter_number"] for item in body["tasks"]] == [1, 2]

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(workflow_id))
            assert workflow is not None
            assert workflow.current_node_id == "chapter_gen"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_regenerate_chapter_tasks_requires_ready_assets(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id, _workflow_id = _seed_project_with_active_workflow(
        session_factory,
        ready_assets=False,
    )
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/chapter-tasks/regenerate",
            json={
                "chapters": [
                    {
                        "chapter_number": 1,
                        "title": "第一章",
                        "brief": "章节计划",
                    }
                ]
            },
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 422
        assert "大纲必须先确认后才能重建章节计划" in response.json()["detail"]
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_list_chapter_tasks_returns_workflow_scoped_tasks(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    _project_id, owner_id, workflow_id = _seed_project_with_tasks(session_factory)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.get(
            f"/api/v1/workflows/{workflow_id}/chapter-tasks",
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 200
        body = response.json()
        assert [item["chapter_number"] for item in body] == [1, 2]
        assert body[0]["title"] == "第一章"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_update_chapter_task_allows_pending_task(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    _project_id, owner_id, workflow_id = _seed_project_with_tasks(session_factory)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.put(
            f"/api/v1/workflows/{workflow_id}/chapter-tasks/2",
            json={
                "brief": "主角在山门外首次反杀并夺得线索",
                "key_events": ["伏击", "反杀", "夺线索"],
            },
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["chapter_number"] == 2
        assert body["brief"] == "主角在山门外首次反杀并夺得线索"
        assert body["key_events"] == ["伏击", "反杀", "夺线索"]
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_update_chapter_task_rejects_completed_task(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    _project_id, owner_id, workflow_id = _seed_project_with_tasks(
        session_factory,
        completed_chapter=2,
    )
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.put(
            f"/api/v1/workflows/{workflow_id}/chapter-tasks/2",
            json={"brief": "不应允许修改"},
            headers=_auth_headers(owner_id),
        )

        assert response.status_code == 422
        assert "不允许编辑" in response.json()["detail"]
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


def _seed_project_with_active_workflow(
    session_factory: sessionmaker[Session],
    *,
    ready_assets: bool,
) -> tuple[str, uuid.UUID, str]:
    with session_factory() as session:
        owner = create_user(session)
        template = create_template(session)
        project = create_project(
            session,
            owner=owner,
            template_id=template.id,
            project_setting=ready_project_setting(),
        )
        workflow = create_workflow(
            session,
            project=project,
            template_id=template.id,
            status="running",
            current_node_id="chapter_split",
            workflow_snapshot=DEFAULT_WORKFLOW_SNAPSHOT,
        )
        if ready_assets:
            _create_asset(session, project.id, "outline", "大纲")
            _create_asset(session, project.id, "opening_plan", "开篇设计")
        return str(project.id), owner.id, str(workflow.id)


def _seed_project_with_tasks(
    session_factory: sessionmaker[Session],
    *,
    completed_chapter: int | None = None,
) -> tuple[str, uuid.UUID, str]:
    project_id, owner_id, workflow_id = _seed_project_with_active_workflow(
        session_factory,
        ready_assets=True,
    )
    with session_factory() as session:
        workflow = session.get(WorkflowExecution, uuid.UUID(workflow_id))
        assert workflow is not None
        create_chapter_task(
            session,
            workflow=workflow,
            chapter_number=1,
            title="第一章",
            brief="第一章摘要",
            status="pending",
        )
        create_chapter_task(
            session,
            workflow=workflow,
            chapter_number=2,
            title="第二章",
            brief="第二章摘要",
            status="completed" if completed_chapter == 2 else "pending",
        )
    return project_id, owner_id, workflow_id


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


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
