from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import WorkflowConfig
from app.modules.content.models import Content
from app.modules.project.models import Project
from app.modules.workflow.engine import InvalidTransitionError, WorkflowStateMachine
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError

from .dto import (
    WorkflowExecutionDTO,
    WorkflowExecutionStatus,
    WorkflowExecutionSummaryDTO,
    WorkflowPauseDTO,
    WorkflowStartDTO,
)
from .snapshot_support import (
    build_runtime_snapshot,
    resolve_start_node_id,
    workflow_to_dto,
    workflow_to_summary_dto,
)
from .workflow_app_runtime_support import RuntimeDispatchFn, WorkflowAppRuntimeSupportMixin
from .workflow_app_service_base import PREPARATION_ASSET_LABELS, WorkflowAppServiceBase
from .workflow_task_runtime_support import ensure_workflow_can_resume


class WorkflowAppService(WorkflowAppRuntimeSupportMixin, WorkflowAppServiceBase):
    async def start_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: WorkflowStartDTO,
        *,
        owner_id: uuid.UUID,
        runtime_dispatcher: RuntimeDispatchFn | None = None,
    ) -> WorkflowExecutionDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_template=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        workflow_config = self._resolve_workflow_config(project, payload.workflow_id)
        await self._ensure_preparation_assets_ready(db, project.id)
        await self._ensure_no_active_workflow(db, project.id)
        workflow = self._build_execution(project, workflow_config)
        await self._persist_started_workflow(db, workflow, workflow_config)
        execution_id = workflow.id
        await self._dispatch_runtime(
            db,
            execution_id,
            owner_id=owner_id,
            runtime_dispatcher=runtime_dispatcher,
        )
        db.expire_all()
        workflow = await self._require_workflow(db, execution_id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    async def pause_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        payload: WorkflowPauseDTO,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = await self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        if workflow.status == "paused":
            return workflow_to_dto(workflow)
        try:
            self.workflow_service.pause(
                workflow,
                reason=payload.reason,
                current_node_id=workflow.current_node_id,
                resume_from_node=workflow.current_node_id,
            )
        except InvalidTransitionError as exc:
            raise ConflictError(f"当前状态不允许暂停工作流: {workflow.status}") from exc
        workflow.snapshot = build_runtime_snapshot(workflow)
        self._record_workflow_log(
            db,
            workflow,
            level="WARNING",
            message="Workflow paused by user",
            details={"reason": payload.reason},
        )
        await db.commit()
        await db.refresh(workflow)
        return workflow_to_dto(workflow)

    async def resume_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        runtime_dispatcher: RuntimeDispatchFn | None = None,
    ) -> WorkflowExecutionDTO:
        workflow = await self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        if workflow.status == "running":
            return workflow_to_dto(workflow)
        await self._ensure_resume_allowed(db, workflow.id)
        execution_id = workflow.id
        try:
            self.workflow_service.resume(workflow)
        except InvalidTransitionError as exc:
            raise ConflictError(f"当前状态不允许恢复工作流: {workflow.status}") from exc
        self._record_workflow_log(db, workflow, level="INFO", message="Workflow resumed")
        await db.commit()
        await self._dispatch_runtime(
            db,
            execution_id,
            owner_id=owner_id,
            runtime_dispatcher=runtime_dispatcher,
        )
        db.expire_all()
        workflow = await self._require_workflow(db, execution_id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    async def cancel_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = await self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        if workflow.status in {"completed", "cancelled"}:
            return workflow_to_dto(workflow)
        try:
            self.workflow_service.cancel(workflow, current_node_id=workflow.current_node_id)
        except InvalidTransitionError as exc:
            raise ConflictError(f"当前状态不允许取消工作流: {workflow.status}") from exc
        self._record_workflow_log(db, workflow, level="WARNING", message="Workflow cancelled")
        await db.commit()
        await db.refresh(workflow)
        return workflow_to_dto(workflow)

    async def get_workflow_detail(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = await self._require_workflow(db, workflow_id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    async def list_project_workflows(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        status: WorkflowExecutionStatus | None = None,
        limit: int = 50,
    ) -> list[WorkflowExecutionSummaryDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        statement = select(WorkflowExecution).where(WorkflowExecution.project_id == project_id)
        if status is not None:
            statement = statement.where(WorkflowExecution.status == status)
        statement = statement.order_by(
            WorkflowExecution.updated_at.desc(),
            WorkflowExecution.completed_at.desc().nulls_last(),
            WorkflowExecution.started_at.desc().nulls_last(),
            WorkflowExecution.created_at.desc(),
            WorkflowExecution.id.desc(),
        ).limit(limit)
        workflows = (await db.scalars(statement)).all()
        return [workflow_to_summary_dto(item) for item in workflows]

    async def _ensure_preparation_assets_ready(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        for asset_type, label in PREPARATION_ASSET_LABELS.items():
            content = await self._find_project_content(db, project_id, asset_type)
            if content is None or content.status != "approved":
                raise BusinessRuleError(f"{label}必须先确认后才能启动工作流")

    async def _find_project_content(
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

    async def _ensure_no_active_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        statement = select(WorkflowExecution.id).where(
            WorkflowExecution.project_id == project_id,
            WorkflowExecution.status.in_(WorkflowStateMachine.ACTIVE_STATES),
        )
        existing = await db.scalar(statement)
        if existing is not None:
            raise ConflictError("项目已存在未结束的工作流，必须先恢复或取消当前执行")

    async def _ensure_resume_allowed(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
    ) -> None:
        await ensure_workflow_can_resume(db, workflow_id)

    async def _persist_started_workflow(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
    ) -> None:
        try:
            db.add(workflow)
            await db.flush()
            self.workflow_service.start(workflow, current_node_id=resolve_start_node_id(workflow_config))
            self._record_workflow_log(db, workflow, level="INFO", message="Workflow started")
            await db.commit()
        except BusinessRuleError:
            await db.rollback()
            raise
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError("项目已存在未结束的工作流，必须先恢复或取消当前执行") from exc
        except InvalidTransitionError as exc:
            await db.rollback()
            raise ConflictError(f"工作流无法启动，当前状态不允许: {exc}") from exc

    async def _require_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(_workflow_statement(workflow_id, owner_id=owner_id))
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    async def _require_workflow_for_update(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        statement = _workflow_statement(workflow_id, owner_id=owner_id).with_for_update()
        workflow = await db.scalar(statement)
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow


def _workflow_statement(
    workflow_id: uuid.UUID,
    *,
    owner_id: uuid.UUID,
):
    return (
        select(WorkflowExecution)
        .join(Project, WorkflowExecution.project_id == Project.id)
        .where(
            WorkflowExecution.id == workflow_id,
            Project.owner_id == owner_id,
        )
    )
