from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class WorkflowAppStartGraphState(TypedDict, total=False):
    workflow_config: Any
    workflow: Any
    execution_id: Any


class LangGraphWorkflowAppStartRuntime:
    def __init__(
        self,
        *,
        resolve_workflow_config: Callable[[], Any],
        ensure_preconditions: Callable[[], Awaitable[None]],
        build_execution: Callable[[Any], Any],
        persist_started_workflow: Callable[[Any, Any], Awaitable[None]],
        dispatch_runtime: Callable[[Any], Awaitable[None]],
    ) -> None:
        self.resolve_workflow_config = resolve_workflow_config
        self.ensure_preconditions = ensure_preconditions
        self.build_execution = build_execution
        self.persist_started_workflow = persist_started_workflow
        self.dispatch_runtime = dispatch_runtime
        self._graph = self._build_graph()

    async def run(self):
        final_state = await self._graph.ainvoke({})
        execution_id = final_state.get("execution_id")
        if execution_id is None:
            raise ConfigurationError("Workflow app start runtime completed without execution id")
        return execution_id

    def _build_graph(self):
        graph = StateGraph(WorkflowAppStartGraphState)
        graph.add_node("resolve_workflow_config", self._resolve_workflow_config)
        graph.add_node("ensure_preconditions", self._ensure_preconditions)
        graph.add_node("build_execution", self._build_execution)
        graph.add_node("persist_started_workflow", self._persist_started_workflow)
        graph.add_node("dispatch_runtime", self._dispatch_runtime)
        graph.add_edge(START, "resolve_workflow_config")
        graph.add_edge("resolve_workflow_config", "ensure_preconditions")
        graph.add_edge("ensure_preconditions", "build_execution")
        graph.add_edge("build_execution", "persist_started_workflow")
        graph.add_edge("persist_started_workflow", "dispatch_runtime")
        graph.add_edge("dispatch_runtime", END)
        return graph.compile(name="workflow_app_start_runtime")

    def _resolve_workflow_config(
        self,
        _state: WorkflowAppStartGraphState,
    ) -> WorkflowAppStartGraphState:
        return {"workflow_config": self.resolve_workflow_config()}

    async def _ensure_preconditions(
        self,
        state: WorkflowAppStartGraphState,
    ) -> WorkflowAppStartGraphState:
        await self.ensure_preconditions()
        return state

    def _build_execution(
        self,
        state: WorkflowAppStartGraphState,
    ) -> WorkflowAppStartGraphState:
        workflow_config = state.get("workflow_config")
        if workflow_config is None:
            raise ConfigurationError("Workflow app start runtime missing workflow config")
        workflow = self.build_execution(workflow_config)
        return {
            "workflow_config": workflow_config,
            "workflow": workflow,
        }

    async def _persist_started_workflow(
        self,
        state: WorkflowAppStartGraphState,
    ) -> WorkflowAppStartGraphState:
        workflow = state.get("workflow")
        workflow_config = state.get("workflow_config")
        if workflow is None or workflow_config is None:
            raise ConfigurationError("Workflow app start runtime missing workflow state")
        await self.persist_started_workflow(workflow, workflow_config)
        execution_id = getattr(workflow, "id", None)
        if execution_id is None:
            raise ConfigurationError("Workflow app start runtime missing workflow id after persist")
        return {**state, "execution_id": execution_id}

    async def _dispatch_runtime(
        self,
        state: WorkflowAppStartGraphState,
    ) -> WorkflowAppStartGraphState:
        execution_id = state.get("execution_id")
        if execution_id is None:
            raise ConfigurationError("Workflow app start runtime missing execution id")
        await self.dispatch_runtime(execution_id)
        return state
