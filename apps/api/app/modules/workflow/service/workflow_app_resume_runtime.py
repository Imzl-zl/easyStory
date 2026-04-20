from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class WorkflowAppResumeGraphState(TypedDict, total=False):
    execution_id: Any


class LangGraphWorkflowAppResumeRuntime:
    def __init__(
        self,
        *,
        ensure_resume_allowed: Callable[[], Awaitable[None]],
        resume_workflow: Callable[[], Awaitable[Any]],
        dispatch_runtime: Callable[[Any], Awaitable[None]],
    ) -> None:
        self.ensure_resume_allowed = ensure_resume_allowed
        self.resume_workflow = resume_workflow
        self.dispatch_runtime = dispatch_runtime
        self._graph = self._build_graph()

    async def run(self):
        final_state = await self._graph.ainvoke({})
        execution_id = final_state.get("execution_id")
        if execution_id is None:
            raise ConfigurationError("Workflow app resume runtime completed without execution id")
        return execution_id

    def _build_graph(self):
        graph = StateGraph(WorkflowAppResumeGraphState)
        graph.add_node("ensure_resume_allowed", self._ensure_resume_allowed)
        graph.add_node("resume_workflow", self._resume_workflow)
        graph.add_node("dispatch_runtime", self._dispatch_runtime)
        graph.add_edge(START, "ensure_resume_allowed")
        graph.add_edge("ensure_resume_allowed", "resume_workflow")
        graph.add_edge("resume_workflow", "dispatch_runtime")
        graph.add_edge("dispatch_runtime", END)
        return graph.compile(name="workflow_app_resume_runtime")

    async def _ensure_resume_allowed(
        self,
        state: WorkflowAppResumeGraphState,
    ) -> WorkflowAppResumeGraphState:
        await self.ensure_resume_allowed()
        return state

    async def _resume_workflow(
        self,
        _state: WorkflowAppResumeGraphState,
    ) -> WorkflowAppResumeGraphState:
        workflow = await self.resume_workflow()
        execution_id = getattr(workflow, "id", None)
        if execution_id is None:
            raise ConfigurationError("Workflow app resume runtime missing workflow id")
        return {"execution_id": execution_id}

    async def _dispatch_runtime(
        self,
        state: WorkflowAppResumeGraphState,
    ) -> WorkflowAppResumeGraphState:
        execution_id = state.get("execution_id")
        if execution_id is None:
            raise ConfigurationError("Workflow app resume runtime missing execution id")
        await self.dispatch_runtime(execution_id)
        return state
