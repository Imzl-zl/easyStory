from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowHookEventGraphState(TypedDict, total=False):
    hooks: list[Any]
    results: list[Any]


class LangGraphWorkflowHookEventRuntime:
    def __init__(
        self,
        *,
        resolve_hooks: Callable[[], list[Any]],
        matches_condition: Callable[[Any], bool],
        record_skip: Callable[[Any], None],
        execute_hook: Callable[[Any], Awaitable[Any]],
        record_success: Callable[[Any, Any], None],
    ) -> None:
        self.resolve_hooks = resolve_hooks
        self.matches_condition = matches_condition
        self.record_skip = record_skip
        self.execute_hook = execute_hook
        self.record_success = record_success
        self._graph = self._build_graph()

    async def run(self) -> list[Any]:
        final_state = await self._graph.ainvoke({})
        return list(final_state.get("results", []))

    def _build_graph(self):
        graph = StateGraph(WorkflowHookEventGraphState)
        graph.add_node("resolve_hooks", self._resolve_hooks)
        graph.add_node("execute_hooks", self._execute_hooks)
        graph.add_edge(START, "resolve_hooks")
        graph.add_edge("resolve_hooks", "execute_hooks")
        graph.add_edge("execute_hooks", END)
        return graph.compile(name="workflow_hook_event_runtime")

    def _resolve_hooks(
        self,
        _state: WorkflowHookEventGraphState,
    ) -> WorkflowHookEventGraphState:
        return {
            "hooks": self.resolve_hooks(),
            "results": [],
        }

    async def _execute_hooks(
        self,
        state: WorkflowHookEventGraphState,
    ) -> WorkflowHookEventGraphState:
        hooks = state.get("hooks") or []
        results: list[Any] = list(state.get("results") or [])
        for hook in hooks:
            if not self.matches_condition(hook):
                self.record_skip(hook)
                continue
            result = await self.execute_hook(hook)
            self.record_success(hook, result)
            results.append(result)
        return {"results": results}
