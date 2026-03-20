from __future__ import annotations

import copy
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.billing.service import create_billing_service
from app.modules.content.models import Content, ContentVersion
from app.modules.credential.models import ModelCredential
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from app.modules.workflow.entry.http.router import get_workflow_app_service
from app.modules.workflow.service import WorkflowRuntimeService, create_workflow_app_service, create_workflow_service
from app.modules.content.service import create_chapter_content_service
from app.modules.context.engine import create_context_builder
from app.modules.export.models import Export
from app.modules.export.service import ExportService
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
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
    client = _build_runtime_client(session_factory)

    try:
        response = client.post(
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
        client.close()
        Base.metadata.drop_all(engine)


def test_start_workflow_requires_confirmed_preparation_assets(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=False)
    client = _build_runtime_client(session_factory)

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
    client = _build_runtime_client(session_factory)

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
    client = _build_runtime_client(session_factory)
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
        assert pause_response.json()["pause_reason"] is None
        assert pause_response.json()["resume_from_node"] == "chapter_gen"
        assert pause_response.json()["has_runtime_snapshot"] is True

        resume_response = client.post(
            f"/api/v1/workflows/{execution_id}/resume",
            headers=headers,
        )
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "paused"
        assert resume_response.json()["current_node_id"] == "chapter_gen"
        assert resume_response.json()["resume_from_node"] == "chapter_gen"

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
    client = _build_runtime_client(session_factory)
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


def test_resume_workflow_waiting_confirmation_keeps_existing_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = _build_runtime_client(session_factory)
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        first_resume = client.post(f"/api/v1/workflows/{execution_id}/resume", headers=headers)
        assert first_resume.status_code == 200
        assert first_resume.json()["status"] == "paused"

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
            assert workflow is not None
            original_snapshot = copy.deepcopy(workflow.snapshot)
            assert original_snapshot["pending_actions"][0]["type"] == "chapter_confirmation"
            assert workflow.pause_reason is None

        second_resume = client.post(f"/api/v1/workflows/{execution_id}/resume", headers=headers)
        assert second_resume.status_code == 422
        assert second_resume.json()["code"] == "business_rule_error"
        assert "待确认" in second_resume.json()["detail"]

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, uuid.UUID(execution_id))
            assert workflow is not None
            assert workflow.snapshot == original_snapshot
            assert workflow.pause_reason is None
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_workflow_runtime_reaches_export_after_chapter_approvals(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    export_root = Path.cwd() / ".pytest-exports" / f"workflow-runtime-{uuid.uuid4().hex}"
    client = _build_runtime_client(session_factory, export_root=export_root)
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        resume_first = client.post(f"/api/v1/workflows/{execution_id}/resume", headers=headers)
        assert resume_first.status_code == 200
        assert resume_first.json()["status"] == "paused"
        assert resume_first.json()["current_node_id"] == "chapter_gen"

        approve_first = client.post(
            f"/api/v1/projects/{project_id}/chapters/1/approve",
            headers=headers,
        )
        assert approve_first.status_code == 200

        resume_second = client.post(f"/api/v1/workflows/{execution_id}/resume", headers=headers)
        assert resume_second.status_code == 200
        assert resume_second.json()["status"] == "paused"

        approve_second = client.post(
            f"/api/v1/projects/{project_id}/chapters/2/approve",
            headers=headers,
        )
        assert approve_second.status_code == 200

        finish_response = client.post(f"/api/v1/workflows/{execution_id}/resume", headers=headers)
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
        client.close()
        Base.metadata.drop_all(engine)
        shutil.rmtree(export_root, ignore_errors=True)


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
        chapter_task = (
            session.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == uuid.UUID(execution_id))
            .filter(ChapterTask.chapter_number == 1)
            .one_or_none()
        )
        assert chapter_task is not None
        chapter_task.status = "stale"
        session.commit()


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}


def _build_runtime_client(
    session_factory: sessionmaker[Session],
    *,
    export_root: Path | None = None,
) -> TestClient:
    app = create_app(session_factory=session_factory)
    workflow_service = create_workflow_service()
    runtime_service = WorkflowRuntimeService(
        workflow_service=workflow_service,
        billing_service=create_billing_service(),
        chapter_content_service=create_chapter_content_service(),
        context_builder=create_context_builder(),
        credential_service_factory=lambda: _FakeCredentialService(),
        export_service=ExportService(export_root or (Path.cwd() / ".pytest-exports")),
        template_renderer=SkillTemplateRenderer(),
        tool_provider=_FakeToolProvider(),
    )
    app.dependency_overrides[get_workflow_app_service] = lambda: create_workflow_app_service(
        workflow_service=workflow_service,
        runtime_service=runtime_service,
    )
    return TestClient(app)


class _FakeCrypto:
    def decrypt(self, value: str) -> str:
        return value


class _FakeCredentialService:
    def __init__(self) -> None:
        self.crypto = _FakeCrypto()

    def resolve_active_credential(
        self,
        db: Session,
        *,
        provider: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ModelCredential:
        del project_id
        credential = (
            db.query(ModelCredential)
            .filter(
                ModelCredential.owner_type == "user",
                ModelCredential.owner_id == user_id,
                ModelCredential.provider == provider,
            )
            .one_or_none()
        )
        if credential is None:
            credential = ModelCredential(
                owner_type="user",
                owner_id=user_id,
                provider=provider,
                display_name=f"{provider}-fake",
                encrypted_key=f"{provider}-fake-key",
                is_active=True,
            )
            db.add(credential)
            db.flush()
        return credential


class _FakeToolProvider(ToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        if "请拆分出可执行的章节任务列表" in prompt:
            return {
                "content": {
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "第一章 逃亡夜",
                            "brief": "主角连夜出逃并暴露追兵",
                            "key_characters": ["林渊"],
                            "key_events": ["夜逃"],
                        },
                        {
                            "chapter_number": 2,
                            "title": "第二章 山门截杀",
                            "brief": "主角在山门外首次反杀",
                            "key_characters": ["林渊"],
                            "key_events": ["反杀"],
                        },
                    ]
                },
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            }
        if "输出一个严格符合 ReviewResult 的 JSON 对象" in prompt:
            return {
                "content": {
                    "reviewer_id": "agent.style_checker",
                    "reviewer_name": "文风检查员",
                    "status": "passed",
                    "score": 92,
                    "issues": [],
                    "summary": "通过",
                    "execution_time_ms": 1,
                    "tokens_used": 10,
                },
                "input_tokens": 8,
                "output_tokens": 8,
                "total_tokens": 16,
            }
        if "第二章 山门截杀" in prompt:
            return {
                "content": "第二章正文：山门外的反杀正式展开。",
                "input_tokens": 15,
                "output_tokens": 40,
                "total_tokens": 55,
            }
        return {
            "content": "第一章正文：林渊在夜色中踏上逃亡之路。",
            "input_tokens": 12,
            "output_tokens": 36,
            "total_tokens": 48,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]
