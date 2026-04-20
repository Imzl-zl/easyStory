from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import BusinessRuleError


class WorkflowAppPersistedGraphState(TypedDict, total=False):
    workflow: Any


class LangGraphWorkflowAppPersistedRuntime:
    def __init__(
        self,
        *,
        load_workflow: Callable[[], Awaitable[Any]],
        run_runtime: Callable[[Any], Awaitable[None]],
        commit: Callable[[], Awaitable[None]],
        recover_runtime_failure: Callable[[str | None, str, str | None], Awaitable[None]],
    ) -> None:
        self.load_workflow = load_workflow
        self.run_runtime = run_runtime
        self.commit = commit
        self.recover_runtime_failure = recover_runtime_failure
        self.current_node_id: str | None = None
        self._graph = self._build_graph()

    async def run(self) -> None:
        try:
            await self._graph.ainvoke({})
        except Exception as exc:
            reason = None if isinstance(exc, BusinessRuleError) else "error"
            await self.recover_runtime_failure(
                self.current_node_id,
                str(exc),
                reason,
            )
            raise

    def _build_graph(self):
        graph = StateGraph(WorkflowAppPersistedGraphState)
        graph.add_node("load_workflow", self._load_workflow)
        graph.add_node("run_runtime", self._run_runtime)
        graph.add_node("commit", self._commit)
        graph.add_edge(START, "load_workflow")
        graph.add_edge("load_workflow", "run_runtime")
        graph.add_edge("run_runtime", "commit")
        graph.add_edge("commit", END)
        return graph.compile(name="workflow_app_persisted_runtime")

    async def _load_workflow(
        self,
        _state: WorkflowAppPersistedGraphState,
    ) -> WorkflowAppPersistedGraphState:
        workflow = await self.load_workflow()
        self.current_node_id = getattr(workflow, "current_node_id", None)
        return {"workflow": workflow}

    async def _run_runtime(
        self,
        state: WorkflowAppPersistedGraphState,
    ) -> WorkflowAppPersistedGraphState:
        workflow = state["workflow"]
        await self.run_runtime(workflow)
        return state

    async def _commit(
        self,
        state: WorkflowAppPersistedGraphState,
    ) -> WorkflowAppPersistedGraphState:
        await self.commit()
        return state
