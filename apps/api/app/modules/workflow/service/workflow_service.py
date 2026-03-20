from __future__ import annotations

from app.modules.workflow.engine import WorkflowEngine
from app.modules.workflow.models import WorkflowExecution


class WorkflowService:
    """Application-layer workflow state operations."""

    def __init__(self, engine: WorkflowEngine) -> None:
        self.engine = engine

    def start(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None = None,
    ) -> WorkflowExecution:
        return self.engine.transition(
            workflow,
            "running",
            current_node_id=current_node_id,
        )

    def pause(
        self,
        workflow: WorkflowExecution,
        *,
        reason: str | None,
        current_node_id: str | None = None,
        resume_from_node: str | None = None,
    ) -> WorkflowExecution:
        if workflow.status == "paused":
            return workflow
        next_node = resume_from_node or current_node_id
        return self.engine.transition(
            workflow,
            "paused",
            current_node_id=current_node_id,
            pause_reason=reason,
            resume_from_node=next_node,
        )

    def resume(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None = None,
    ) -> WorkflowExecution:
        if workflow.status == "running":
            return workflow
        node_id = current_node_id or workflow.resume_from_node
        return self.engine.transition(
            workflow,
            "running",
            current_node_id=node_id,
        )

    def complete(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None = None,
    ) -> WorkflowExecution:
        return self.engine.transition(
            workflow,
            "completed",
            current_node_id=current_node_id,
        )

    def fail(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None = None,
    ) -> WorkflowExecution:
        return self.engine.transition(
            workflow,
            "failed",
            current_node_id=current_node_id,
        )

    def cancel(
        self,
        workflow: WorkflowExecution,
        *,
        current_node_id: str | None = None,
    ) -> WorkflowExecution:
        if workflow.status in {"completed", "cancelled"}:
            return workflow
        return self.engine.transition(
            workflow,
            "cancelled",
            current_node_id=current_node_id,
        )
