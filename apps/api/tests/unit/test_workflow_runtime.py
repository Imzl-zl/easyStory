from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content, ContentVersion
from app.modules.content.service import create_chapter_content_service
from app.modules.context.engine import create_context_builder
from app.modules.export.models import Export
from app.modules.export.service import ExportService
from app.modules.observability.models import PromptReplay
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, ChapterTask, NodeExecution, WorkflowExecution
from app.modules.workflow.service import WorkflowRuntimeService, WorkflowService, create_workflow_service
from app.modules.workflow.service.snapshot_support import (
    dump_config, freeze_agents, freeze_skills, freeze_workflow, resolve_start_node_id,
)
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting

CONFIG_ROOT = Path(__file__).resolve().parents[4] / "config"

@dataclass(frozen=True)
class RuntimeHarness:
    chapter_content_service: Any
    export_root: Path
    owner_id: uuid.UUID
    project_id: uuid.UUID
    runtime_service: WorkflowRuntimeService
    workflow: WorkflowExecution
    workflow_service: WorkflowService


def test_runtime_chapter_split_persists_tasks_artifact_and_prompt_replay(db) -> None:
    harness = _build_runtime_harness(db)
    try:
        harness.runtime_service.run(db, harness.workflow, owner_id=harness.owner_id)
        db.commit()
        db.refresh(harness.workflow)
        chapter_tasks = _list_chapter_tasks(db, harness.workflow.id)
        node_executions = _list_node_executions(db, harness.workflow.id)
        artifacts = db.query(Artifact).all()
        replays = db.query(PromptReplay).all()
        assert harness.workflow.status == "paused"
        assert harness.workflow.current_node_id == "chapter_split"
        assert harness.workflow.resume_from_node == "chapter_gen"
        assert harness.workflow.snapshot["completed_nodes"] == [
            {"node_id": "chapter_split", "sequence": 0, "status": "completed"}
        ]
        assert [task.chapter_number for task in chapter_tasks] == [1, 2]
        assert [task.status for task in chapter_tasks] == ["pending", "pending"]
        assert [(item.node_id, item.sequence, item.status) for item in node_executions] == [
            ("chapter_split", 0, "completed")
        ]
        assert artifacts[0].artifact_type == "chapter_tasks"
        assert artifacts[0].payload["chapters"][0]["title"] == "第一章 逃亡夜"
        assert '"chapters"' in (replays[0].response_text or "")
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def test_runtime_manual_flow_generates_reviewed_chapters_and_exports(db) -> None:
    harness = _build_runtime_harness(db)
    try:
        harness.runtime_service.run(db, harness.workflow, owner_id=harness.owner_id)
        db.commit()
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter_one = _require_chapter(db, harness.project_id, 1)
        version_one = _require_current_version(chapter_one)
        assert harness.workflow.status == "paused"
        assert harness.workflow.current_node_id == "chapter_gen"
        assert harness.workflow.resume_from_node == "chapter_gen"
        assert harness.workflow.snapshot["current_chapter_number"] == 1
        assert version_one.created_by == "ai_assist"
        assert version_one.change_source == "ai_generate"
        assert "林渊在夜色中踏上逃亡之路" in version_one.content_text
        assert [item.status for item in _list_chapter_tasks(db, harness.workflow.id)] == [
            "generating",
            "pending",
        ]
        assert [item.status for item in db.query(ReviewAction).all()] == ["passed"]

        harness.chapter_content_service.approve_chapter(db, harness.project_id, 1)
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        chapter_two = _require_chapter(db, harness.project_id, 2)
        version_two = _require_current_version(chapter_two)
        assert version_two.created_by == "ai_assist"
        assert "山门外的反杀正式展开" in version_two.content_text
        assert [item.status for item in _list_chapter_tasks(db, harness.workflow.id)] == [
            "completed",
            "generating",
        ]
        assert [item.status for item in db.query(ReviewAction).order_by(ReviewAction.created_at.asc()).all()] == [
            "passed",
            "passed",
        ]

        harness.chapter_content_service.approve_chapter(db, harness.project_id, 2)
        db.refresh(harness.workflow)
        _resume_and_run(db, harness)
        exports = db.query(Export).order_by(Export.format.asc()).all()
        node_executions = _list_node_executions(db, harness.workflow.id)
        assert harness.workflow.status == "completed"
        assert harness.workflow.snapshot is None
        assert [task.status for task in _list_chapter_tasks(db, harness.workflow.id)] == [
            "completed",
            "completed",
        ]
        assert [item.node_id for item in node_executions] == [
            "chapter_split",
            "chapter_gen",
            "chapter_gen",
            "export",
        ]
        assert [item.format for item in exports] == ["markdown", "txt"]
        for item in exports:
            file_path = harness.export_root / Path(item.file_path)
            content = file_path.read_text(encoding="utf-8")
            assert not Path(item.file_path).is_absolute()
            assert file_path.exists()
            assert "林渊在夜色中踏上逃亡之路" in content
            assert "山门外的反杀正式展开" in content
    finally:
        shutil.rmtree(harness.export_root, ignore_errors=True)


def _build_runtime_harness(db: Session) -> RuntimeHarness:
    owner = create_user(db)
    template = create_template(db)
    project = create_project(
        db,
        owner=owner,
        template_id=template.id,
        project_setting=ready_project_setting(),
    )
    _create_asset(db, project.id, "outline", "大纲")
    _create_asset(db, project.id, "opening_plan", "开篇设计")
    config_loader = ConfigLoader(CONFIG_ROOT)
    workflow_config = config_loader.load_workflow("workflow.xuanhuan_manual")
    agents = freeze_agents(config_loader, workflow_config)
    workflow = WorkflowExecution(
        project_id=project.id,
        template_id=project.template_id,
        status="created",
        workflow_snapshot=freeze_workflow(config_loader, workflow_config),
        skills_snapshot=freeze_skills(config_loader, workflow_config, agents),
        agents_snapshot={agent.id: dump_config(agent) for agent in agents},
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    workflow_service = create_workflow_service()
    workflow_service.start(workflow, current_node_id=resolve_start_node_id(workflow_config))
    export_root = Path.cwd() / ".pytest-exports" / f"workflow-runtime-{uuid.uuid4().hex}"
    runtime_service = WorkflowRuntimeService(
        workflow_service=workflow_service,
        chapter_content_service=create_chapter_content_service(),
        context_builder=create_context_builder(),
        credential_service_factory=lambda: _FakeCredentialService(),
        export_service=ExportService(export_root),
        template_renderer=SkillTemplateRenderer(),
        tool_provider=_FakeToolProvider(),
    )
    db.commit()
    db.refresh(workflow)
    return RuntimeHarness(
        chapter_content_service=runtime_service.chapter_content_service,
        export_root=export_root,
        owner_id=owner.id,
        project_id=project.id,
        runtime_service=runtime_service,
        workflow=workflow,
        workflow_service=workflow_service,
    )


def _create_asset(
    db: Session,
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
    db.add(content)
    db.flush()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=f"{title}内容",
        )
    )
    db.commit()


def _list_chapter_tasks(db: Session, workflow_id: uuid.UUID) -> list[ChapterTask]:
    return (
        db.query(ChapterTask)
        .filter(ChapterTask.workflow_execution_id == workflow_id)
        .order_by(ChapterTask.chapter_number.asc())
        .all()
    )


def _list_node_executions(db: Session, workflow_id: uuid.UUID) -> list[NodeExecution]:
    return (
        db.query(NodeExecution)
        .filter(NodeExecution.workflow_execution_id == workflow_id)
        .order_by(NodeExecution.node_order.asc(), NodeExecution.sequence.asc())
        .all()
    )


def _require_chapter(db: Session, project_id: uuid.UUID, chapter_number: int) -> Content:
    chapter = (
        db.query(Content)
        .filter(
            Content.project_id == project_id,
            Content.content_type == "chapter",
            Content.chapter_number == chapter_number,
        )
        .one_or_none()
    )
    assert chapter is not None
    return chapter


def _require_current_version(content: Content) -> ContentVersion:
    version = next((item for item in content.versions if item.is_current), None)
    assert version is not None
    return version


def _resume_and_run(db: Session, harness: RuntimeHarness) -> None:
    harness.workflow_service.resume(harness.workflow)
    harness.runtime_service.run(db, harness.workflow, owner_id=harness.owner_id)
    db.commit()
    db.refresh(harness.workflow)


class _FakeCrypto:
    def decrypt(self, value: str) -> str:
        return value


class _FakeCredential:
    def __init__(self, encrypted_key: str, base_url: str | None = None) -> None:
        self.encrypted_key = encrypted_key
        self.base_url = base_url


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
    ) -> _FakeCredential:
        del db, user_id, project_id
        return _FakeCredential(encrypted_key=f"{provider}-fake-key")


class _FakeToolProvider(ToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        if "请拆分出可执行的章节任务列表" in prompt:
            return {
                "content": json.dumps(
                    {
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
                    ensure_ascii=False,
                ),
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
            return {"content": "第二章正文：山门外的反杀正式展开。"}
        return {"content": "第一章正文：林渊在夜色中踏上逃亡之路。"}

    def list_tools(self) -> list[str]:
        return ["llm.generate"]
