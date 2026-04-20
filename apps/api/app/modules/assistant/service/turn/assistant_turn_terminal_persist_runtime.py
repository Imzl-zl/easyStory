from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class AssistantTurnTerminalPersistGraphState(TypedDict, total=False):
    existing_run: Any | None
    record: Any


class LangGraphAssistantTurnTerminalPersistRuntime:
    def __init__(
        self,
        *,
        resolve_existing_run: Callable[[], Any | None],
        build_terminal_record: Callable[[Any | None], Any],
        save_run: Callable[[Any], None],
    ) -> None:
        self.resolve_existing_run = resolve_existing_run
        self.build_terminal_record = build_terminal_record
        self.save_run = save_run
        self._graph = self._build_graph()

    def run(self) -> None:
        self._graph.invoke({})

    def _build_graph(self):
        graph = StateGraph(AssistantTurnTerminalPersistGraphState)
        graph.add_node("resolve_existing_run", self._resolve_existing_run)
        graph.add_node("build_terminal_record", self._build_terminal_record)
        graph.add_node("save_run", self._save_run)
        graph.add_edge(START, "resolve_existing_run")
        graph.add_edge("resolve_existing_run", "build_terminal_record")
        graph.add_edge("build_terminal_record", "save_run")
        graph.add_edge("save_run", END)
        return graph.compile(name="assistant_turn_terminal_persist_runtime")

    def _resolve_existing_run(
        self,
        _state: AssistantTurnTerminalPersistGraphState,
    ) -> AssistantTurnTerminalPersistGraphState:
        return {"existing_run": self.resolve_existing_run()}

    def _build_terminal_record(
        self,
        state: AssistantTurnTerminalPersistGraphState,
    ) -> AssistantTurnTerminalPersistGraphState:
        return {
            "record": self.build_terminal_record(state.get("existing_run")),
        }

    def _save_run(
        self,
        state: AssistantTurnTerminalPersistGraphState,
    ) -> AssistantTurnTerminalPersistGraphState:
        record = state.get("record")
        if record is None:
            raise ConfigurationError("Assistant terminal persist runtime missing terminal record")
        self.save_run(record)
        return {}
