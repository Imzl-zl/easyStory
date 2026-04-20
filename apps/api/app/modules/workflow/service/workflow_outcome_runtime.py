from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.modules.config_registry.schemas.config_schemas import NodeConfig
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import build_runtime_snapshot
from .workflow_runtime_shared import NodeOutcome


class WorkflowOutcomeGraphState(TypedDict, total=False):
    terminated: bool


class LangGraphWorkflowOutcomeRuntime:
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
        self._graph = self._build_graph()

    def run(self) -> bool:
        final_state = self._graph.invoke({})
        terminated = final_state.get("terminated")
        if not isinstance(terminated, bool):
            raise ConfigurationError("Workflow outcome runtime completed without terminated flag")
        return terminated

    def _build_graph(self):
        graph = StateGraph(WorkflowOutcomeGraphState)
        graph.add_node("apply_failed", self._apply_failed)
        graph.add_node("apply_paused", self._apply_paused)
        graph.add_node("apply_completed", self._apply_completed)
        graph.add_node("apply_continue", self._apply_continue)
        graph.add_conditional_edges(
            START,
            self._route_initial_state,
            {
                "apply_failed": "apply_failed",
                "apply_paused": "apply_paused",
                "apply_completed": "apply_completed",
                "apply_continue": "apply_continue",
            },
        )
        graph.add_edge("apply_failed", END)
        graph.add_edge("apply_paused", END)
        graph.add_edge("apply_completed", END)
        graph.add_edge("apply_continue", END)
        return graph.compile(name="workflow_outcome_runtime")

    def _route_initial_state(self, _state: WorkflowOutcomeGraphState) -> str:
        if self.outcome.workflow_status == "failed":
            return "apply_failed"
        if self.outcome.pause_reason is not None or self.outcome.snapshot_extra is not None:
            return "apply_paused"
        if self.outcome.next_node_id is None:
            return "apply_completed"
        return "apply_continue"

    def _apply_failed(self, _state: WorkflowOutcomeGraphState) -> WorkflowOutcomeGraphState:
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
        return {"terminated": True}

    def _apply_paused(self, _state: WorkflowOutcomeGraphState) -> WorkflowOutcomeGraphState:
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
        return {"terminated": True}

    def _apply_completed(self, _state: WorkflowOutcomeGraphState) -> WorkflowOutcomeGraphState:
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
        return {"terminated": True}

    def _apply_continue(self, _state: WorkflowOutcomeGraphState) -> WorkflowOutcomeGraphState:
        next_node_id = self.outcome.next_node_id
        if next_node_id is None:
            raise ConfigurationError("Workflow outcome runtime missing next node id")
        self.workflow.current_node_id = next_node_id
        self.workflow.snapshot = None
        return {"terminated": False}
