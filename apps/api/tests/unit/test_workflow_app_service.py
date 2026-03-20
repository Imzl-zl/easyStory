from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.modules.workflow.service import WorkflowAppService, create_workflow_service
from app.modules.workflow.service.dto import WorkflowStartDTO
from app.modules.project.service import create_project_service
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting

CONFIG_ROOT = Path(__file__).resolve().parents[4] / "config"
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


def test_start_workflow_recovers_paused_state_after_runtime_flush_failure(db) -> None:
    owner, project = _create_ready_project(db)
    service = _build_service(_FailingRuntimeService())

    with pytest.raises(IntegrityError):
        service.start_workflow(db, project.id, WorkflowStartDTO(), owner_id=owner.id)

    workflow = (
        db.query(WorkflowExecution)
        .filter(WorkflowExecution.project_id == project.id)
        .one()
    )

    assert workflow.status == "paused"
    assert workflow.pause_reason == "error"
    assert workflow.current_node_id == "chapter_split"
    assert workflow.resume_from_node == "chapter_split"
    assert workflow.snapshot["pending_actions"][0]["type"] == "runtime_error"
    assert db.query(ChapterTask).count() == 0


def test_resume_workflow_recovers_paused_state_after_runtime_flush_failure(db) -> None:
    owner, project = _create_ready_project(db)
    workflow = WorkflowExecution(
        project_id=project.id,
        template_id=project.template_id,
        status="paused",
        current_node_id="chapter_gen",
        resume_from_node="chapter_gen",
        workflow_snapshot=WORKFLOW_SNAPSHOT,
        skills_snapshot={},
        agents_snapshot={},
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    service = _build_service(_FailingRuntimeService())

    with pytest.raises(IntegrityError):
        service.resume_workflow(db, workflow.id, owner_id=owner.id)

    db.refresh(workflow)
    assert workflow.status == "paused"
    assert workflow.pause_reason == "error"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.resume_from_node == "chapter_gen"
    assert workflow.snapshot["pending_actions"][0]["type"] == "runtime_error"
    assert db.query(ChapterTask).count() == 0


def _build_service(runtime_service) -> WorkflowAppService:
    return WorkflowAppService(
        workflow_service=create_workflow_service(),
        project_service=create_project_service(),
        config_loader=ConfigLoader(CONFIG_ROOT),
        runtime_service=runtime_service,
    )


def _create_ready_project(db):
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
    return owner, project


def _create_asset(db, project_id, content_type, title):
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
            is_current=True,
        )
    )
    db.commit()


class _FailingRuntimeService:
    def run(self, db, workflow, *, owner_id):
        del owner_id
        db.add(
            ChapterTask(
                project_id=workflow.project_id,
                workflow_execution_id=None,
                chapter_number=1,
                title="非法任务",
                brief="触发 flush 失败",
                status="pending",
            )
        )
        db.flush()
