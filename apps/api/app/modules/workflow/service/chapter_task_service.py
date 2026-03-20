from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.project.models import Project
from app.modules.project.service import ProjectService
from app.modules.workflow.engine import WorkflowStateMachine
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError

from .chapter_task_dto import (
    ChapterTaskBatchDTO,
    ChapterTaskDraftDTO,
    ChapterTaskRegenerateDTO,
    ChapterTaskUpdateDTO,
    ChapterTaskViewDTO,
)
from .snapshot_support import resolve_next_node_id

PREPARATION_ASSET_LABELS = {
    "outline": "大纲",
    "opening_plan": "开篇设计",
}
EDITABLE_CHAPTER_TASK_STATUSES = frozenset({"pending", "generating", "failed", "stale", "interrupted"})


class ChapterTaskService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    def regenerate_tasks(
        self,
        db: Session,
        project_id: uuid.UUID,
        payload: ChapterTaskRegenerateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ChapterTaskBatchDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        self._ensure_preparation_assets_ready(db, project.id)
        workflow = self._require_active_workflow(db, project.id)
        self._replace_tasks(db, workflow, payload.chapters)
        self._advance_workflow_after_regenerate(workflow)
        db.commit()
        return self._build_batch_response(db, workflow)

    def list_tasks(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[ChapterTaskViewDTO]:
        workflow = self._require_workflow(db, workflow_id, owner_id=owner_id)
        return self._list_workflow_tasks(db, workflow.id)

    def update_task(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        chapter_number: int,
        payload: ChapterTaskUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ChapterTaskViewDTO:
        self._require_workflow(db, workflow_id, owner_id=owner_id)
        task = self._require_task(db, workflow_id, chapter_number)
        self._ensure_task_editable(task)
        self._apply_task_update(task, payload)
        db.commit()
        db.refresh(task)
        return self._to_view(task)

    def _ensure_preparation_assets_ready(
        self,
        db: Session,
        project_id: uuid.UUID,
    ) -> None:
        for content_type, label in PREPARATION_ASSET_LABELS.items():
            content = self._find_content(db, project_id, content_type)
            if content is None or content.status != "approved":
                raise BusinessRuleError(f"{label}必须先确认后才能重建章节计划")

    def _replace_tasks(
        self,
        db: Session,
        workflow: WorkflowExecution,
        chapters: list[ChapterTaskDraftDTO],
    ) -> None:
        (
            db.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == workflow.id)
            .delete(synchronize_session=False)
        )
        db.flush()
        for chapter in sorted(chapters, key=lambda item: item.chapter_number):
            db.add(
                ChapterTask(
                    project_id=workflow.project_id,
                    workflow_execution_id=workflow.id,
                    chapter_number=chapter.chapter_number,
                    title=chapter.title.strip(),
                    brief=chapter.brief.strip(),
                    key_characters=list(chapter.key_characters),
                    key_events=list(chapter.key_events),
                    status="pending",
                )
            )

    def _advance_workflow_after_regenerate(
        self,
        workflow: WorkflowExecution,
    ) -> None:
        next_node_id = resolve_next_node_id(
            workflow.workflow_snapshot or {},
            current_node_id="chapter_split",
        )
        if next_node_id is None:
            return
        workflow.current_node_id = next_node_id
        if workflow.status == "paused":
            workflow.resume_from_node = next_node_id

    def _build_batch_response(
        self,
        db: Session,
        workflow: WorkflowExecution,
    ) -> ChapterTaskBatchDTO:
        return ChapterTaskBatchDTO(
            project_id=workflow.project_id,
            workflow_execution_id=workflow.id,
            current_node_id=workflow.current_node_id,
            tasks=self._list_workflow_tasks(db, workflow.id),
        )

    def _list_workflow_tasks(
        self,
        db: Session,
        workflow_id: uuid.UUID,
    ) -> list[ChapterTaskViewDTO]:
        tasks = (
            db.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == workflow_id)
            .order_by(ChapterTask.chapter_number.asc())
            .all()
        )
        return [self._to_view(task) for task in tasks]

    def _require_active_workflow(
        self,
        db: Session,
        project_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = (
            db.query(WorkflowExecution)
            .filter(
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.status.in_(WorkflowStateMachine.ACTIVE_STATES),
            )
            .with_for_update()
            .one_or_none()
        )
        if workflow is None:
            raise ConflictError("项目当前没有活跃工作流，无法重建章节计划")
        return workflow

    def _require_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = (
            db.query(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .filter(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
            .one_or_none()
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    def _require_task(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        chapter_number: int,
    ) -> ChapterTask:
        task = (
            db.query(ChapterTask)
            .filter(
                ChapterTask.workflow_execution_id == workflow_id,
                ChapterTask.chapter_number == chapter_number,
            )
            .one_or_none()
        )
        if task is None:
            raise NotFoundError(
                f"ChapterTask not found: workflow={workflow_id}, chapter={chapter_number}"
            )
        return task

    def _ensure_task_editable(self, task: ChapterTask) -> None:
        if task.status not in EDITABLE_CHAPTER_TASK_STATUSES:
            raise BusinessRuleError(f"当前章节任务状态不允许编辑: {task.status}")

    def _apply_task_update(
        self,
        task: ChapterTask,
        payload: ChapterTaskUpdateDTO,
    ) -> None:
        if payload.title is not None:
            task.title = payload.title.strip()
        if payload.brief is not None:
            task.brief = payload.brief.strip()
        if payload.key_characters is not None:
            task.key_characters = list(payload.key_characters)
        if payload.key_events is not None:
            task.key_events = list(payload.key_events)

    def _find_content(
        self,
        db: Session,
        project_id: uuid.UUID,
        content_type: str,
    ) -> Content | None:
        return (
            db.query(Content)
            .filter(
                Content.project_id == project_id,
                Content.content_type == content_type,
            )
            .one_or_none()
        )

    def _to_view(self, task: ChapterTask) -> ChapterTaskViewDTO:
        return ChapterTaskViewDTO(
            task_id=task.id,
            project_id=task.project_id,
            workflow_execution_id=task.workflow_execution_id,
            chapter_number=task.chapter_number,
            title=task.title,
            brief=task.brief,
            key_characters=list(task.key_characters or []),
            key_events=list(task.key_events or []),
            status=task.status,
            content_id=task.content_id,
        )
