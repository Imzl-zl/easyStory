import pytest

from app.modules.assistant.service.turn.assistant_turn_terminal_persist_runtime import (
    LangGraphAssistantTurnTerminalPersistRuntime,
)
from app.shared.runtime.errors import ConfigurationError


def test_assistant_turn_terminal_persist_runtime_builds_and_saves_record() -> None:
    call_log: list[object] = []
    existing_run = object()
    record = object()

    runtime = LangGraphAssistantTurnTerminalPersistRuntime(
        resolve_existing_run=lambda: call_log.append("resolve_existing_run") or existing_run,
        build_terminal_record=lambda value: call_log.append(("build_terminal_record", value)) or record,
        save_run=lambda value: call_log.append(("save_run", value)),
    )

    runtime.run()

    assert call_log == [
        "resolve_existing_run",
        ("build_terminal_record", existing_run),
        ("save_run", record),
    ]


def test_assistant_turn_terminal_persist_runtime_requires_record() -> None:
    runtime = LangGraphAssistantTurnTerminalPersistRuntime(
        resolve_existing_run=lambda: None,
        build_terminal_record=lambda value: None,
        save_run=lambda value: None,
    )

    with pytest.raises(
        ConfigurationError,
        match="Assistant terminal persist runtime missing terminal record",
    ):
        runtime.run()
