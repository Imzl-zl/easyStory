from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse


class AssistantTurnExecutionGraphState(TypedDict, total=False):
    before_results: list[Any]
    raw_output: LLMGenerateToolResponse
    response: Any


class LangGraphAssistantTurnExecutionRuntime:
    def __init__(
        self,
        *,
        run_before_hooks: Callable[[], Awaitable[list[Any]]],
        call_turn_llm: Callable[[], Awaitable[LLMGenerateToolResponse]],
        finalize_response: Callable[[list[Any], LLMGenerateToolResponse], Awaitable[Any]],
        run_prepared_on_error_hooks: Callable[[Exception], Awaitable[Exception | None]],
        store_terminal_turn: Callable[..., None],
    ) -> None:
        self.run_before_hooks = run_before_hooks
        self.call_turn_llm = call_turn_llm
        self.finalize_response = finalize_response
        self.run_prepared_on_error_hooks = run_prepared_on_error_hooks
        self.store_terminal_turn = store_terminal_turn
        self._graph = self._build_graph()

    async def run(self) -> Any:
        try:
            final_state = await self._graph.ainvoke({})
        except Exception as exc:
            hook_error = await self.run_prepared_on_error_hooks(exc)
            self.store_terminal_turn(error=hook_error or exc)
            if hook_error is not None:
                raise hook_error
            raise
        response = final_state.get("response")
        if response is None:
            raise ConfigurationError("Assistant turn execution completed without response")
        self.store_terminal_turn(response=response)
        return response

    def _build_graph(self):
        graph = StateGraph(AssistantTurnExecutionGraphState)
        graph.add_node("run_before_hooks", self._run_before_hooks)
        graph.add_node("call_turn_llm", self._call_turn_llm)
        graph.add_node("finalize_response", self._finalize_response)
        graph.add_edge(START, "run_before_hooks")
        graph.add_edge("run_before_hooks", "call_turn_llm")
        graph.add_edge("call_turn_llm", "finalize_response")
        graph.add_edge("finalize_response", END)
        return graph.compile(name="assistant_turn_execution_runtime")

    async def _run_before_hooks(
        self,
        _state: AssistantTurnExecutionGraphState,
    ) -> AssistantTurnExecutionGraphState:
        return {"before_results": await self.run_before_hooks()}

    async def _call_turn_llm(
        self,
        _state: AssistantTurnExecutionGraphState,
    ) -> AssistantTurnExecutionGraphState:
        return {"raw_output": await self.call_turn_llm()}

    async def _finalize_response(
        self,
        state: AssistantTurnExecutionGraphState,
    ) -> AssistantTurnExecutionGraphState:
        before_results = state.get("before_results")
        raw_output = state.get("raw_output")
        if before_results is None or raw_output is None:
            raise ConfigurationError("Assistant turn execution runtime missing intermediate state")
        return {
            "response": await self.finalize_response(before_results, raw_output),
        }
