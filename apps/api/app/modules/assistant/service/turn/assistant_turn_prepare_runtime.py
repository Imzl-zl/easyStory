from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import ConfigurationError

from ..dto import AssistantTurnResponseDTO
from .assistant_turn_runtime_support import PreparedAssistantTurn


@dataclass(frozen=True)
class AssistantTurnPrepareRuntimeResult:
    resolved_hooks: list[HookConfig]
    prepared: PreparedAssistantTurn
    replayed_response: AssistantTurnResponseDTO | None


class AssistantTurnPrepareGraphState(TypedDict, total=False):
    prepared: PreparedAssistantTurn


class LangGraphAssistantTurnPrepareRuntime:
    def __init__(
        self,
        *,
        resolve_hooks: Callable[[], list[HookConfig]],
        prepare_turn: Callable[[list[HookConfig]], Awaitable[PreparedAssistantTurn]],
        run_prepare_on_error_hooks: Callable[[list[HookConfig], Exception], Awaitable[Exception | None]],
        recover_or_start_turn: Callable[[PreparedAssistantTurn], AssistantTurnResponseDTO | None],
    ) -> None:
        self.resolve_hooks = resolve_hooks
        self.prepare_turn = prepare_turn
        self.run_prepare_on_error_hooks = run_prepare_on_error_hooks
        self.recover_or_start_turn = recover_or_start_turn
        self.resolved_hooks: list[HookConfig] = []
        self._graph = self._build_graph()

    async def run(self) -> AssistantTurnPrepareRuntimeResult:
        try:
            final_state = await self._graph.ainvoke({})
        except Exception as exc:
            hook_error = await self.run_prepare_on_error_hooks(self.resolved_hooks, exc)
            if hook_error is not None:
                raise hook_error
            raise
        prepared = final_state.get("prepared")
        if prepared is None:
            raise ConfigurationError("Assistant turn prepare runtime completed without prepared turn")
        replayed_response = self.recover_or_start_turn(prepared)
        return AssistantTurnPrepareRuntimeResult(
            resolved_hooks=list(self.resolved_hooks),
            prepared=prepared,
            replayed_response=replayed_response,
        )

    def _build_graph(self):
        graph = StateGraph(AssistantTurnPrepareGraphState)
        graph.add_node("resolve_hooks", self._resolve_hooks)
        graph.add_node("prepare_turn", self._prepare_turn)
        graph.add_edge(START, "resolve_hooks")
        graph.add_edge("resolve_hooks", "prepare_turn")
        graph.add_edge("prepare_turn", END)
        return graph.compile(name="assistant_turn_prepare_runtime")

    def _resolve_hooks(
        self,
        _state: AssistantTurnPrepareGraphState,
    ) -> AssistantTurnPrepareGraphState:
        self.resolved_hooks = self.resolve_hooks()
        return {}

    async def _prepare_turn(
        self,
        _state: AssistantTurnPrepareGraphState,
    ) -> AssistantTurnPrepareGraphState:
        return {"prepared": await self.prepare_turn(self.resolved_hooks)}
