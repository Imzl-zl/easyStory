from __future__ import annotations

from datetime import datetime, timezone

from app.modules.workflow.engine.state_machine import WorkflowStateMachine
from app.modules.workflow.models import WorkflowExecution


TERMINAL_WORKFLOW_STATES = frozenset({"completed", "failed", "cancelled"})


class WorkflowEngine:
    """State transition helper for workflow runtime entities."""

    def transition(
        self,
        workflow: WorkflowExecution,
        target_status: str,
        *,
        current_node_id: str | None = None,
        pause_reason: str | None = None,
        resume_from_node: str | None = None,
    ) -> WorkflowExecution:
        WorkflowStateMachine.validate_transition(workflow.status, target_status)
        self._validate_pause_payload(target_status, pause_reason)
        workflow.status = target_status
        if current_node_id is not None:
            workflow.current_node_id = current_node_id
        workflow.pause_reason = pause_reason if target_status == "paused" else None
        workflow.resume_from_node = (
            resume_from_node if target_status == "paused" else None
        )
        self._apply_timestamps(workflow, target_status)
        return workflow

    def _validate_pause_payload(
        self,
        target_status: str,
        pause_reason: str | None,
    ) -> None:
        if target_status != "paused" and pause_reason is not None:
            raise ValueError("pause_reason is only allowed when target_status is paused")
        WorkflowStateMachine.validate_pause_reason(pause_reason)

    def _apply_timestamps(
        self,
        workflow: WorkflowExecution,
        target_status: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        if target_status == "running":
            workflow.started_at = workflow.started_at or now
            workflow.completed_at = None
            return
        if target_status in TERMINAL_WORKFLOW_STATES:
            workflow.completed_at = now
