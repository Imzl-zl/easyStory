from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.config_registry import ConfigLoader
from app.modules.content.models import Content, ContentVersion
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.modules.workflow.service import create_workflow_app_service, create_workflow_service
from app.modules.workflow.service.dto import WorkflowStartDTO
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
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


async def test_start_workflow_recovers_paused_state_after_runtime_flush_failure(tmp_path) -> None:
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-app-start")
    )
    try:
        with session_factory() as session:
            owner, project = _create_ready_project(session)
            owner_id = owner.id
            project_id = project.id
        service = _build_service(_FailingRuntimeService())

        async with async_session_factory() as session:
            with pytest.raises(IntegrityError):
                await service.start_workflow(
                    session,
                    project_id,
                    WorkflowStartDTO(),
                    owner_id=owner_id,
                )

        with session_factory() as session:
            workflow = session.scalars(
                select(WorkflowExecution).where(WorkflowExecution.project_id == project_id)
            ).one()
            assert workflow.status == "paused"
            assert workflow.pause_reason == "error"
            assert workflow.current_node_id == "chapter_split"
            assert workflow.resume_from_node == "chapter_split"
            assert workflow.snapshot["pending_actions"][0]["type"] == "runtime_error"
            assert session.query(ChapterTask).count() == 0
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_resume_workflow_recovers_paused_state_after_runtime_flush_failure(tmp_path) -> None:
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-app-resume")
    )
    try:
        with session_factory() as session:
            owner, project = _create_ready_project(session)
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
            session.add(workflow)
            session.commit()
            session.refresh(workflow)
            owner_id = owner.id
            workflow_id = workflow.id
        service = _build_service(_FailingRuntimeService())

        async with async_session_factory() as session:
            with pytest.raises(IntegrityError):
                await service.resume_workflow(
                    session,
                    workflow_id,
                    owner_id=owner_id,
                )

        with session_factory() as session:
            workflow = session.get(WorkflowExecution, workflow_id)
            assert workflow is not None
            assert workflow.status == "paused"
            assert workflow.pause_reason == "error"
            assert workflow.current_node_id == "chapter_gen"
            assert workflow.resume_from_node == "chapter_gen"
            assert workflow.snapshot["pending_actions"][0]["type"] == "runtime_error"
            assert session.query(ChapterTask).count() == 0
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _build_service(runtime_service):
    return create_workflow_app_service(
        workflow_service=create_workflow_service(),
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
    async def run(self, db, workflow, *, owner_id):
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
        await db.flush()
