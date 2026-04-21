from __future__ import annotations

from collections.abc import Callable

from app.modules.config_registry.schemas.config_schemas import NodeConfig
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import build_runtime_snapshot
from .workflow_runtime_shared import NodeOutcome

class WorkflowOutcomeRuntime:
    def __init__(
        self,
        *,
        workflow_service,
        record_execution_log: Callable[..., None],
        db,
        workflow: WorkflowExecution,
        node: NodeConfig,
        outcome: NodeOutcome,
    ) -> None:
        self.workflow_service = workflow_service
        self.record_execution_log = record_execution_log
        self.db = db
        self.workflow = workflow
        self.node = node
        self.outcome = outcome

    async def run(self) -> bool:
        if self.outcome.workflow_status == "failed":
            return self._apply_failed()
        if self.outcome.pause_reason is not None or self.outcome.snapshot_extra is not None:
            return self._apply_paused()
        if self.outcome.next_node_id is None:
            return self._apply_completed()
        return self._apply_continue()

    def _apply_failed(self) -> bool:
        self.workflow_service.fail(
            self.workflow,
            current_node_id=self.outcome.next_node_id or self.node.id,
        )
        self.workflow.snapshot = build_runtime_snapshot(self.workflow, extra=self.outcome.snapshot_extra)
        self.record_execution_log(
            self.db,
            workflow_execution_id=self.workflow.id,
            node_execution_id=None,
            level="ERROR",
            message="Workflow failed",
            details={"node_id": self.node.id},
        )
        return True

    def _apply_paused(self) -> bool:
        self.workflow_service.pause(
            self.workflow,
            reason=self.outcome.pause_reason,
            current_node_id=self.node.id,
            resume_from_node=self.outcome.next_node_id,
        )
        self.workflow.snapshot = build_runtime_snapshot(self.workflow, extra=self.outcome.snapshot_extra)
        self.record_execution_log(
            self.db,
            workflow_execution_id=self.workflow.id,
            node_execution_id=None,
            level="WARNING" if self.outcome.pause_reason else "INFO",
            message="Workflow paused",
            details={"node_id": self.node.id, "reason": self.outcome.pause_reason},
        )
        return True

    def _apply_completed(self) -> bool:
        self.workflow_service.complete(
            self.workflow,
            current_node_id=self.node.id,
        )
        self.workflow.snapshot = None
        self.record_execution_log(
            self.db,
            workflow_execution_id=self.workflow.id,
            node_execution_id=None,
            level="INFO",
            message="Workflow completed",
            details={"node_id": self.node.id},
        )
        return True

    def _apply_continue(self) -> bool:
        next_node_id = self.outcome.next_node_id
        if next_node_id is None:
            raise ConfigurationError("Workflow outcome runtime missing next node id")
        self.workflow.current_node_id = next_node_id
        self.workflow.snapshot = None
        return False
