from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.project.models import Project
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import NotFoundError

from .dto import (
    ArtifactViewDTO,
    ExecutionLogViewDTO,
    NodeExecutionViewDTO,
    PromptReplayViewDTO,
    ReviewActionViewDTO,
)

TERMINAL_WORKFLOW_STATUSES = frozenset({"completed", "failed", "cancelled"})


class WorkflowObservabilityService:
    def list_node_executions(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[NodeExecutionViewDTO]:
        self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        executions = (
            db.query(NodeExecution)
            .options(
                selectinload(NodeExecution.artifacts),
                selectinload(NodeExecution.review_actions),
            )
            .filter(NodeExecution.workflow_execution_id == workflow_id)
            .order_by(NodeExecution.node_order.asc(), NodeExecution.sequence.asc())
            .all()
        )
        return [self._to_node_execution_dto(item) for item in executions]

    def list_execution_logs(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        level: str | None = None,
        limit: int = 50,
    ) -> list[ExecutionLogViewDTO]:
        self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        query = db.query(ExecutionLog).filter(ExecutionLog.workflow_execution_id == workflow_id)
        if level is not None:
            query = query.filter(ExecutionLog.level == level)
        logs = query.order_by(ExecutionLog.created_at.desc(), ExecutionLog.id.desc()).limit(limit).all()
        return [ExecutionLogViewDTO.model_validate(item, from_attributes=True) for item in logs]

    def list_execution_logs_since(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        after_created_at: datetime | None,
        after_id: uuid.UUID | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[ExecutionLogViewDTO]:
        self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        query = db.query(ExecutionLog).filter(ExecutionLog.workflow_execution_id == workflow_id)
        if level is not None:
            query = query.filter(ExecutionLog.level == level)
        if after_created_at is not None:
            query = query.filter(self._build_after_cursor(after_created_at, after_id))
        logs = query.order_by(ExecutionLog.created_at.asc(), ExecutionLog.id.asc()).limit(limit).all()
        return [ExecutionLogViewDTO.model_validate(item, from_attributes=True) for item in logs]

    def is_workflow_terminal(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> bool:
        workflow = self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        return workflow.status in TERMINAL_WORKFLOW_STATUSES

    def list_prompt_replays(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[PromptReplayViewDTO]:
        self._require_owned_node_execution(
            db,
            workflow_id,
            node_execution_id,
            owner_id=owner_id,
        )
        replays = (
            db.query(PromptReplay)
            .filter(PromptReplay.node_execution_id == node_execution_id)
            .order_by(PromptReplay.created_at.asc())
            .all()
        )
        return [PromptReplayViewDTO.model_validate(item, from_attributes=True) for item in replays]

    def _require_owned_workflow(
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

    def _require_owned_node_execution(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> NodeExecution:
        execution = (
            db.query(NodeExecution)
            .join(WorkflowExecution, NodeExecution.workflow_execution_id == WorkflowExecution.id)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .filter(
                NodeExecution.id == node_execution_id,
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
            .one_or_none()
        )
        if execution is None:
            raise NotFoundError(f"Node execution not found: {node_execution_id}")
        return execution

    def _build_after_cursor(
        self,
        after_created_at: datetime,
        after_id: uuid.UUID | None,
    ):
        if after_id is None:
            return ExecutionLog.created_at > after_created_at
        return or_(
            ExecutionLog.created_at > after_created_at,
            and_(
                ExecutionLog.created_at == after_created_at,
                ExecutionLog.id > after_id,
            ),
        )

    def _to_node_execution_dto(self, execution: NodeExecution) -> NodeExecutionViewDTO:
        input_data = execution.input_data if isinstance(execution.input_data, dict) else {}
        artifacts = sorted(execution.artifacts, key=lambda item: item.created_at)
        actions = sorted(execution.review_actions, key=lambda item: item.created_at)
        return NodeExecutionViewDTO(
            id=execution.id,
            workflow_execution_id=execution.workflow_execution_id,
            node_id=execution.node_id,
            sequence=execution.sequence,
            node_order=execution.node_order,
            node_type=execution.node_type,
            status=execution.status,
            input_summary=self._build_input_summary(input_data),
            context_report=self._context_report(input_data),
            output_data=execution.output_data,
            retry_count=execution.retry_count,
            error_message=execution.error_message,
            execution_time_ms=execution.execution_time_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            artifacts=[ArtifactViewDTO.model_validate(item, from_attributes=True) for item in artifacts],
            review_actions=[self._to_review_action(item) for item in actions],
        )

    def _build_input_summary(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in input_data.items()
            if key in {"skill_id", "model_name", "provider", "chapter_task_id", "chapter_number"}
        }

    def _context_report(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        report = input_data.get("context_report")
        return report if isinstance(report, dict) else None

    def _to_review_action(self, action) -> ReviewActionViewDTO:
        score = float(action.score) if isinstance(action.score, Decimal) else action.score
        return ReviewActionViewDTO(
            id=action.id,
            agent_id=action.agent_id,
            reviewer_name=action.reviewer_name,
            review_type=action.review_type,
            status=action.status,
            score=score,
            summary=action.summary,
            issues=action.issues,
            execution_time_ms=action.execution_time_ms,
            tokens_used=action.tokens_used,
            created_at=action.created_at,
        )
