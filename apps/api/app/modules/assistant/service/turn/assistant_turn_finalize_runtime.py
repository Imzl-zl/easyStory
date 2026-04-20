from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class AssistantTurnFinalizeGraphState(TypedDict, total=False):
    content: str
    after_payload: dict[str, Any]
    after_results: list[Any]
    response: Any


class LangGraphAssistantTurnFinalizeRuntime:
    def __init__(
        self,
        *,
        resolve_content: Callable[[], str],
        build_after_payload: Callable[[str], dict[str, Any]],
        run_after_hooks: Callable[[dict[str, Any]], Awaitable[list[Any]]],
        build_response: Callable[[str, list[Any]], Any],
    ) -> None:
        self.resolve_content = resolve_content
        self.build_after_payload = build_after_payload
        self.run_after_hooks = run_after_hooks
        self.build_response = build_response
        self._graph = self._build_graph()

    async def run(self) -> Any:
        final_state = await self._graph.ainvoke({})
        response = final_state.get("response")
        if response is None:
            raise ConfigurationError("Assistant turn finalize runtime completed without response")
        return response

    def _build_graph(self):
        graph = StateGraph(AssistantTurnFinalizeGraphState)
        graph.add_node("resolve_content", self._resolve_content)
        graph.add_node("build_after_payload", self._build_after_payload)
        graph.add_node("run_after_hooks", self._run_after_hooks)
        graph.add_node("build_response", self._build_response)
        graph.add_edge(START, "resolve_content")
        graph.add_edge("resolve_content", "build_after_payload")
        graph.add_edge("build_after_payload", "run_after_hooks")
        graph.add_edge("run_after_hooks", "build_response")
        graph.add_edge("build_response", END)
        return graph.compile(name="assistant_turn_finalize_runtime")

    def _resolve_content(
        self,
        _state: AssistantTurnFinalizeGraphState,
    ) -> AssistantTurnFinalizeGraphState:
        return {"content": self.resolve_content()}

    def _build_after_payload(
        self,
        state: AssistantTurnFinalizeGraphState,
    ) -> AssistantTurnFinalizeGraphState:
        content = state.get("content")
        if content is None:
            raise ConfigurationError("Assistant turn finalize runtime missing content")
        return {"after_payload": self.build_after_payload(content)}

    async def _run_after_hooks(
        self,
        state: AssistantTurnFinalizeGraphState,
    ) -> AssistantTurnFinalizeGraphState:
        after_payload = state.get("after_payload")
        if after_payload is None:
            raise ConfigurationError("Assistant turn finalize runtime missing after payload")
        return {"after_results": await self.run_after_hooks(after_payload)}

    def _build_response(
        self,
        state: AssistantTurnFinalizeGraphState,
    ) -> AssistantTurnFinalizeGraphState:
        content = state.get("content")
        after_results = state.get("after_results")
        if content is None or after_results is None:
            raise ConfigurationError("Assistant turn finalize runtime missing response state")
        return {
            "response": self.build_response(content, after_results),
        }
