from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError

from .workflow_runtime_shared import NodeOutcome


class WorkflowNodeExecutionGraphState(TypedDict, total=False):
    outcome: NodeOutcome


class LangGraphWorkflowNodeExecutionRuntime:
    def __init__(
        self,
        *,
        run_before_hook: Callable[[], Awaitable[object]],
        run_before_on_error: Callable[[Exception], Awaitable[None]],
        dispatch_node: Callable[[], Awaitable[NodeOutcome]],
        run_dispatch_on_error: Callable[[Exception], Awaitable[None]],
        run_after_hook: Callable[[NodeOutcome], Awaitable[object]],
        run_after_on_error: Callable[[NodeOutcome, Exception], Awaitable[None]],
    ) -> None:
        self.run_before_hook = run_before_hook
        self.run_before_on_error = run_before_on_error
        self.dispatch_node = dispatch_node
        self.run_dispatch_on_error = run_dispatch_on_error
        self.run_after_hook = run_after_hook
        self.run_after_on_error = run_after_on_error
        self._graph = self._build_graph()

    async def run(self) -> NodeOutcome:
        final_state = await self._graph.ainvoke({})
        outcome = final_state.get("outcome")
        if outcome is None:
            raise ConfigurationError("Workflow node execution runtime completed without outcome")
        return outcome

    def _build_graph(self):
        graph = StateGraph(WorkflowNodeExecutionGraphState)
        graph.add_node("run_before_hook", self._run_before_hook)
        graph.add_node("dispatch_node", self._dispatch_node)
        graph.add_node("run_after_hook", self._run_after_hook)
        graph.add_edge(START, "run_before_hook")
        graph.add_edge("run_before_hook", "dispatch_node")
        graph.add_edge("dispatch_node", "run_after_hook")
        graph.add_edge("run_after_hook", END)
        return graph.compile(name="workflow_node_execution_runtime")

    async def _run_before_hook(
        self,
        _state: WorkflowNodeExecutionGraphState,
    ) -> WorkflowNodeExecutionGraphState:
        try:
            await self.run_before_hook()
        except Exception as exc:
            await self.run_before_on_error(exc)
            raise
        return {}

    async def _dispatch_node(
        self,
        _state: WorkflowNodeExecutionGraphState,
    ) -> WorkflowNodeExecutionGraphState:
        try:
            outcome = await self.dispatch_node()
        except Exception as exc:
            await self.run_dispatch_on_error(exc)
            raise
        return {"outcome": outcome}

    async def _run_after_hook(
        self,
        state: WorkflowNodeExecutionGraphState,
    ) -> WorkflowNodeExecutionGraphState:
        outcome = state.get("outcome")
        if outcome is None:
            raise ConfigurationError("Workflow node execution runtime missing dispatch outcome")
        try:
            await self.run_after_hook(outcome)
        except Exception as exc:
            await self.run_after_on_error(outcome, exc)
            raise
        return {"outcome": outcome}
