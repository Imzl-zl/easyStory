from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class AssistantTurnRecoveryGraphState(TypedDict, total=False):
    existing_run: Any | None
    running_record: Any
    create_succeeded: bool
    replayed_response: Any | None


class LangGraphAssistantTurnRecoveryRuntime:
    def __init__(
        self,
        *,
        resolve_existing_run: Callable[[], Any | None],
        recover_existing_running_turn: Callable[[Any], None],
        recover_existing_turn: Callable[[Any], Any | None],
        build_running_turn_record: Callable[[], Any],
        create_run: Callable[[Any], bool],
        reload_existing_run_after_conflict: Callable[[], Any | None],
    ) -> None:
        self.resolve_existing_run = resolve_existing_run
        self.recover_existing_running_turn = recover_existing_running_turn
        self.recover_existing_turn = recover_existing_turn
        self.build_running_turn_record = build_running_turn_record
        self.create_run = create_run
        self.reload_existing_run_after_conflict = reload_existing_run_after_conflict
        self._graph = self._build_graph()

    def run(self) -> Any | None:
        final_state = self._graph.invoke({})
        return final_state.get("replayed_response")

    def _build_graph(self):
        graph = StateGraph(AssistantTurnRecoveryGraphState)
        graph.add_node("resolve_existing_run", self._resolve_existing_run)
        graph.add_node("recover_existing_run", self._recover_existing_run)
        graph.add_node("build_running_turn_record", self._build_running_turn_record)
        graph.add_node("create_run", self._create_run)
        graph.add_node("reload_existing_run_after_conflict", self._reload_existing_run_after_conflict)
        graph.add_node("finish", self._finish)
        graph.add_edge(START, "resolve_existing_run")
        graph.add_conditional_edges(
            "resolve_existing_run",
            self._route_after_resolve_existing_run,
            {
                "recover_existing_run": "recover_existing_run",
                "build_running_turn_record": "build_running_turn_record",
            },
        )
        graph.add_edge("build_running_turn_record", "create_run")
        graph.add_conditional_edges(
            "create_run",
            self._route_after_create_run,
            {
                "finish": "finish",
                "reload_existing_run_after_conflict": "reload_existing_run_after_conflict",
            },
        )
        graph.add_edge("reload_existing_run_after_conflict", "recover_existing_run")
        graph.add_edge("recover_existing_run", "finish")
        graph.add_edge("finish", END)
        return graph.compile(name="assistant_turn_recovery_runtime")

    def _resolve_existing_run(
        self,
        _state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        return {"existing_run": self.resolve_existing_run()}

    def _route_after_resolve_existing_run(
        self,
        state: AssistantTurnRecoveryGraphState,
    ) -> str:
        if state.get("existing_run") is not None:
            return "recover_existing_run"
        return "build_running_turn_record"

    def _recover_existing_run(
        self,
        state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        existing_run = state.get("existing_run")
        if existing_run is None:
            raise ConfigurationError("Assistant turn recovery runtime missing existing run")
        self.recover_existing_running_turn(existing_run)
        return {"replayed_response": self.recover_existing_turn(existing_run)}

    def _build_running_turn_record(
        self,
        _state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        return {"running_record": self.build_running_turn_record()}

    def _create_run(
        self,
        state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        running_record = state.get("running_record")
        if running_record is None:
            raise ConfigurationError("Assistant turn recovery runtime missing running record")
        return {"create_succeeded": self.create_run(running_record)}

    def _route_after_create_run(
        self,
        state: AssistantTurnRecoveryGraphState,
    ) -> str:
        if state.get("create_succeeded") is True:
            return "finish"
        return "reload_existing_run_after_conflict"

    def _reload_existing_run_after_conflict(
        self,
        _state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        existing_run = self.reload_existing_run_after_conflict()
        if existing_run is None:
            raise ConfigurationError(
                "Assistant turn run snapshot disappeared after create_run conflict"
            )
        return {"existing_run": existing_run}

    def _finish(
        self,
        state: AssistantTurnRecoveryGraphState,
    ) -> AssistantTurnRecoveryGraphState:
        return state
