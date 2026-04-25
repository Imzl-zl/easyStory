from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import WorkflowConfig
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import resolve_node_config
from .workflow_graph_runtime_support import resolve_workflow_graph_recursion_limit
from .workflow_runtime_shared import NodeOutcome

if TYPE_CHECKING:
    from .workflow_runtime_service import WorkflowRuntimeService


class WorkflowGraphState(TypedDict, total=False):
    current_node_id: str
    node_outcome: NodeOutcome
    terminated: bool


class WorkflowGraphRuntime:
    def __init__(
        self,
        runtime_service: "WorkflowRuntimeService",
        *,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        owner_id: uuid.UUID,
    ) -> None:
        self.runtime_service = runtime_service
        self.db = db
        self.workflow = workflow
        self.workflow_config = workflow_config
        self.owner_id = owner_id
        self._graph = self._build_graph()

    async def run(self) -> WorkflowExecution:
        current_node_id = self.workflow.current_node_id
        if not current_node_id:
            raise ConfigurationError("Workflow current node is required before runtime execution")
        recursion_limit = await self._resolve_recursion_limit()
        await self._graph.ainvoke(
            {"current_node_id": current_node_id, "terminated": False},
            config={"recursion_limit": recursion_limit},
        )
        return self.workflow

    async def _resolve_recursion_limit(self) -> int:
        loop_item_count = await self._count_runtime_loop_items()
        return resolve_workflow_graph_recursion_limit(
            len(self.workflow_config.nodes),
            runtime_loop_item_count=loop_item_count,
        )

    async def _count_runtime_loop_items(self) -> int:
        statement = (
            select(func.count())
            .select_from(ChapterTask)
            .where(ChapterTask.workflow_execution_id == self.workflow.id)
        )
        return int(await self.db.scalar(statement) or 0)

    def _build_graph(self):
        graph = StateGraph(WorkflowGraphState)
        graph.add_node("execute_node", self._execute_node)
        graph.add_node("apply_outcome", self._apply_outcome)
        graph.add_edge(START, "execute_node")
        graph.add_edge("execute_node", "apply_outcome")
        graph.add_conditional_edges(
            "apply_outcome",
            self._route_after_outcome,
            {
                "continue": "execute_node",
                "stop": END,
            },
        )
        return graph.compile(name="workflow_runtime")

    async def _execute_node(self, state: WorkflowGraphState) -> WorkflowGraphState:
        node = resolve_node_config(self.workflow_config, state["current_node_id"])
        outcome = await self.runtime_service.execute_node(
            self.db,
            self.workflow,
            self.workflow_config,
            node,
            owner_id=self.owner_id,
        )
        return {"node_outcome": outcome}

    async def _apply_outcome(self, state: WorkflowGraphState) -> WorkflowGraphState:
        current_node_id = state.get("current_node_id")
        outcome = state.get("node_outcome")
        if not current_node_id or outcome is None:
            raise ConfigurationError("Workflow graph state is missing current node execution result")
        node = resolve_node_config(self.workflow_config, current_node_id)
        terminated = await self.runtime_service.apply_outcome_async(
            self.db,
            self.workflow,
            node,
            outcome,
        )
        next_state: WorkflowGraphState = {"terminated": terminated}
        if not terminated:
            next_node_id = self.workflow.current_node_id or outcome.next_node_id
            if next_node_id is None:
                raise ConfigurationError("Workflow graph did not resolve a next node")
            next_state["current_node_id"] = next_node_id
        return next_state

    def _route_after_outcome(self, state: WorkflowGraphState) -> str:
        return "stop" if state.get("terminated", False) else "continue"
