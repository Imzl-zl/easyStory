from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import WorkflowConfig
from app.modules.content.models import Content
from app.modules.observability.models import ExecutionLog
from app.modules.project.models import Project
from app.modules.project.service import ProjectService
from app.modules.workflow.engine import InvalidTransitionError, WorkflowStateMachine
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import (
    BusinessRuleError,
    ConfigurationError,
    ConflictError,
    NotFoundError,
)

from .dto import WorkflowExecutionDTO, WorkflowPauseDTO, WorkflowStartDTO
from .snapshot_support import (
    build_runtime_snapshot,
    dump_config,
    freeze_agents,
    freeze_skills,
    freeze_workflow,
    resolve_start_node_id,
    workflow_to_dto,
)
from .workflow_task_runtime_support import ensure_workflow_can_resume
from .workflow_runtime_service import WorkflowRuntimeService
from .workflow_service import WorkflowService

PREPARATION_ASSET_LABELS = {
    "outline": "大纲",
    "opening_plan": "开篇设计",
}

class WorkflowAppService:
    def __init__(
        self,
        workflow_service: WorkflowService,
        project_service: ProjectService,
        config_loader: ConfigLoader,
        runtime_service: WorkflowRuntimeService,
    ) -> None:
        self.workflow_service = workflow_service
        self.project_service = project_service
        self.config_loader = config_loader
        self.runtime_service = runtime_service

    def start_workflow(
        self,
        db: Session,
        project_id: uuid.UUID,
        payload: WorkflowStartDTO,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        project = self.project_service.require_project(db, project_id, owner_id=owner_id)
        self.project_service.ensure_setting_allows_preparation(project)
        workflow_config = self._resolve_workflow_config(project, payload.workflow_id)
        self._ensure_preparation_assets_ready(db, project.id)
        self._ensure_no_active_workflow(db, project.id)
        workflow = self._build_execution(project, workflow_config)
        self._persist_started_workflow(db, workflow, workflow_config)
        self._run_persisted_workflow(db, workflow.id, owner_id=owner_id)
        workflow = self._require_workflow(db, workflow.id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    def pause_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        payload: WorkflowPauseDTO,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
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
        db.commit()
        db.refresh(workflow)
        return workflow_to_dto(workflow)

    def resume_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        if workflow.status == "running":
            return workflow_to_dto(workflow)
        self._ensure_resume_allowed(db, workflow.id)
        try:
            self.workflow_service.resume(workflow)
        except InvalidTransitionError as exc:
            raise ConflictError(f"当前状态不允许恢复工作流: {workflow.status}") from exc
        self._record_workflow_log(db, workflow, level="INFO", message="Workflow resumed")
        db.commit()
        self._run_persisted_workflow(db, workflow.id, owner_id=owner_id)
        workflow = self._require_workflow(db, workflow.id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    def cancel_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        if workflow.status in {"completed", "cancelled"}:
            return workflow_to_dto(workflow)
        try:
            self.workflow_service.cancel(
                workflow,
                current_node_id=workflow.current_node_id,
            )
        except InvalidTransitionError as exc:
            raise ConflictError(f"当前状态不允许取消工作流: {workflow.status}") from exc
        self._record_workflow_log(db, workflow, level="WARNING", message="Workflow cancelled")
        db.commit()
        db.refresh(workflow)
        return workflow_to_dto(workflow)

    def get_workflow_detail(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecutionDTO:
        workflow = self._require_workflow(db, workflow_id, owner_id=owner_id)
        return workflow_to_dto(workflow)

    def _resolve_workflow_config(
        self,
        project: Project,
        requested_workflow_id: str | None,
    ) -> WorkflowConfig:
        workflow_id = requested_workflow_id or _extract_template_workflow_id(project)
        if workflow_id is None:
            raise BusinessRuleError("项目未绑定默认工作流，请显式指定 workflow_id")
        return self.config_loader.load_workflow(workflow_id)

    def _ensure_preparation_assets_ready(
        self,
        db: Session,
        project_id: uuid.UUID,
    ) -> None:
        for asset_type, label in PREPARATION_ASSET_LABELS.items():
            content = self._find_project_content(db, project_id, asset_type)
            if content is None or content.status != "approved":
                raise BusinessRuleError(f"{label}必须先确认后才能启动工作流")

    def _find_project_content(
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

    def _ensure_no_active_workflow(
        self,
        db: Session,
        project_id: uuid.UUID,
    ) -> None:
        existing = (
            db.query(WorkflowExecution.id)
            .filter(
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.status.in_(WorkflowStateMachine.ACTIVE_STATES),
            )
            .one_or_none()
        )
        if existing is not None:
            raise ConflictError("项目已存在未结束的工作流，必须先恢复或取消当前执行")

    def _build_execution(
        self,
        project: Project,
        workflow_config: WorkflowConfig,
    ) -> WorkflowExecution:
        agents = freeze_agents(self.config_loader, workflow_config)
        return WorkflowExecution(
            project_id=project.id,
            template_id=project.template_id,
            status="created",
            workflow_snapshot=freeze_workflow(
                self.config_loader,
                workflow_config,
            ),
            skills_snapshot=freeze_skills(
                self.config_loader,
                workflow_config,
                agents,
            ),
            agents_snapshot={agent.id: dump_config(agent) for agent in agents},
        )

    def _ensure_resume_allowed(
        self,
        db: Session,
        workflow_id: uuid.UUID,
    ) -> None:
        ensure_workflow_can_resume(db, workflow_id)

    def _persist_started_workflow(
        self,
        db: Session,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
    ) -> None:
        try:
            db.add(workflow)
            db.flush()
            self.workflow_service.start(
                workflow,
                current_node_id=resolve_start_node_id(workflow_config),
            )
            self._record_workflow_log(db, workflow, level="INFO", message="Workflow started")
            db.commit()
        except BusinessRuleError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("项目已存在未结束的工作流，必须先恢复或取消当前执行") from exc
        except InvalidTransitionError as exc:
            db.rollback()
            raise ConflictError(f"工作流无法启动，当前状态不允许: {exc}") from exc

    def _run_persisted_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        workflow = self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        current_node_id = workflow.current_node_id
        try:
            self.runtime_service.run(db, workflow, owner_id=owner_id)
            db.commit()
        except BusinessRuleError as exc:
            self._recover_runtime_failure(
                db,
                workflow_id=workflow_id,
                owner_id=owner_id,
                current_node_id=current_node_id,
                detail=str(exc),
                reason=None,
            )
            raise
        except Exception as exc:
            self._recover_runtime_failure(
                db,
                workflow_id=workflow_id,
                owner_id=owner_id,
                current_node_id=current_node_id,
                detail=str(exc),
                reason="error",
            )
            raise

    def _recover_runtime_failure(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        current_node_id: str | None,
        detail: str,
        reason: str | None,
    ) -> None:
        db.rollback()
        workflow = self._require_workflow_for_update(db, workflow_id, owner_id=owner_id)
        self._pause_after_runtime_error(
            workflow,
            current_node_id=current_node_id,
            detail=detail,
            reason=reason,
        )
        self._record_workflow_log(
            db,
            workflow,
            level="ERROR",
            message="Workflow paused after runtime error",
            details={"detail": detail, "reason": reason},
        )
        db.commit()

    def _require_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = self._workflow_query(db, workflow_id, owner_id).one_or_none()
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    def _require_workflow_for_update(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = (
            self._workflow_query(db, workflow_id, owner_id)
            .with_for_update()
            .one_or_none()
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    def _workflow_query(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Query[WorkflowExecution]:
        return (
            db.query(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .filter(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
        )

    def _pause_after_runtime_error(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None,
        detail: str,
        reason: str | None,
    ) -> None:
        self.workflow_service.pause(
            workflow,
            reason=reason,
            current_node_id=current_node_id,
            resume_from_node=current_node_id,
        )
        workflow.snapshot = build_runtime_snapshot(
            workflow,
            extra={"pending_actions": [{"type": "runtime_error", "detail": detail}]},
        )

    def _record_workflow_log(
        self,
        db: Session,
        workflow: WorkflowExecution,
        *,
        level: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        db.add(
            ExecutionLog(
                workflow_execution_id=workflow.id,
                node_execution_id=None,
                level=level,
                message=message,
                details=details,
            )
        )


def _extract_template_workflow_id(project: Project) -> str | None:
    template = project.template
    if template is None or template.config is None:
        return None
    workflow_id = template.config.get("workflow_id")
    if workflow_id is None:
        return None
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ConfigurationError("Template.config.workflow_id must be a non-empty string")
    return workflow_id
