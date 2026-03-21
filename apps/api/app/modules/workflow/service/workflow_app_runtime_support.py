from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from app.modules.config_registry.schemas.config_schemas import WorkflowConfig
from app.modules.observability.models import ExecutionLog
from app.modules.project.models import Project
from app.modules.workflow.engine import InvalidTransitionError
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError

from .snapshot_support import build_runtime_snapshot, resolve_start_node_id


class WorkflowAppRuntimeSupportMixin:
    def run_workflow_runtime(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        self._run_persisted_workflow(db, workflow_id, owner_id=owner_id)

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
        workflow = self._workflow_query(db, workflow_id, owner_id).with_for_update().one_or_none()
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
