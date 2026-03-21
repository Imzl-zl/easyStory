from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from .chapter_task_support import (
    PREPARATION_ASSET_LABELS,
    advance_workflow_after_regenerate,
    apply_task_update,
    ensure_task_editable,
    to_view,
)


class ChapterTaskService:
    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    async def regenerate_tasks(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ChapterTaskRegenerateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ChapterTaskBatchDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        await self._ensure_preparation_assets_ready(db, project.id)
        workflow = await self._require_active_workflow(db, project.id)
        await self._replace_tasks(db, workflow, payload.chapters)
        advance_workflow_after_regenerate(workflow)
        await db.commit()
        return await self._build_batch_response(db, workflow)

    async def list_tasks(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[ChapterTaskViewDTO]:
        workflow = await self._require_workflow(db, workflow_id, owner_id=owner_id)
        return await self._list_workflow_tasks(db, workflow.id)

    async def update_task(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        chapter_number: int,
        payload: ChapterTaskUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ChapterTaskViewDTO:
        await self._require_workflow(db, workflow_id, owner_id=owner_id)
        task = await self._require_task(db, workflow_id, chapter_number)
        ensure_task_editable(task)
        apply_task_update(task, payload)
        await db.commit()
        await db.refresh(task)
        return to_view(task)

    async def _ensure_preparation_assets_ready(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        for content_type, label in PREPARATION_ASSET_LABELS.items():
            content = await self._find_content(db, project_id, content_type)
            if content is None or content.status != "approved":
                raise BusinessRuleError(f"{label}必须先确认后才能重建章节计划")

    async def _replace_tasks(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        chapters: list[ChapterTaskDraftDTO],
    ) -> None:
        statement = delete(ChapterTask).where(ChapterTask.workflow_execution_id == workflow.id)
        await db.execute(statement)
        await db.flush()
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

    async def _build_batch_response(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
    ) -> ChapterTaskBatchDTO:
        return ChapterTaskBatchDTO(
            project_id=workflow.project_id,
            workflow_execution_id=workflow.id,
            current_node_id=workflow.current_node_id,
            tasks=await self._list_workflow_tasks(db, workflow.id),
        )

    async def _list_workflow_tasks(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
    ) -> list[ChapterTaskViewDTO]:
        statement = (
            select(ChapterTask)
            .where(ChapterTask.workflow_execution_id == workflow_id)
            .order_by(ChapterTask.chapter_number.asc())
        )
        tasks = (await db.scalars(statement)).all()
        return [to_view(task) for task in tasks]

    async def _require_active_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.status.in_(WorkflowStateMachine.ACTIVE_STATES),
            )
            .with_for_update()
        )
        if workflow is None:
            raise ConflictError("项目当前没有活跃工作流，无法重建章节计划")
        return workflow

    async def _require_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(
            select(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .where(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    async def _require_task(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        chapter_number: int,
    ) -> ChapterTask:
        task = await db.scalar(
            select(ChapterTask).where(
                ChapterTask.workflow_execution_id == workflow_id,
                ChapterTask.chapter_number == chapter_number,
            )
        )
        if task is None:
            raise NotFoundError(
                f"ChapterTask not found: workflow={workflow_id}, chapter={chapter_number}"
            )
        return task

    async def _find_content(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_type: str,
    ) -> Content | None:
        statement = select(Content).where(
            Content.project_id == project_id,
            Content.content_type == content_type,
        )
        return await db.scalar(statement)
