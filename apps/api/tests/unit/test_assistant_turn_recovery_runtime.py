import pytest

from app.modules.assistant.service.turn.assistant_turn_recovery_runtime import (
    LangGraphAssistantTurnRecoveryRuntime,
)
from app.shared.runtime.errors import ConfigurationError


def test_assistant_turn_recovery_runtime_recovers_existing_run() -> None:
    call_log: list[object] = []
    existing_run = object()
    replayed_response = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: existing_run,
        recover_existing_running_turn=lambda value: call_log.append(("recover_running", value)),
        recover_existing_turn=lambda value: call_log.append(("recover", value)) or replayed_response,
        build_running_turn_record=lambda: (_ for _ in ()).throw(
            AssertionError("should not build record")
        ),
        create_run=lambda record: (_ for _ in ()).throw(AssertionError("should not create run")),
        reload_existing_run_after_conflict=lambda: (_ for _ in ()).throw(
            AssertionError("should not reload conflict")
        ),
    )

    result = runtime.run()

    assert result is replayed_response
    assert call_log == [
        ("recover_running", existing_run),
        ("recover", existing_run),
    ]


def test_assistant_turn_recovery_runtime_creates_new_run_without_replay() -> None:
    call_log: list[object] = []
    running_record = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: None,
        recover_existing_running_turn=lambda value: call_log.append(("recover_running", value)),
        recover_existing_turn=lambda value: call_log.append(("recover", value)),
        build_running_turn_record=lambda: call_log.append("build_record") or running_record,
        create_run=lambda record: call_log.append(("create", record)) or True,
        reload_existing_run_after_conflict=lambda: call_log.append("reload"),
    )

    result = runtime.run()

    assert result is None
    assert call_log == [
        "build_record",
        ("create", running_record),
    ]


def test_assistant_turn_recovery_runtime_recovers_after_create_conflict() -> None:
    call_log: list[object] = []
    running_record = object()
    existing_run = object()
    replayed_response = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: None,
        recover_existing_running_turn=lambda value: call_log.append(("recover_running", value)),
        recover_existing_turn=lambda value: call_log.append(("recover", value)) or replayed_response,
        build_running_turn_record=lambda: call_log.append("build_record") or running_record,
        create_run=lambda record: call_log.append(("create", record)) or False,
        reload_existing_run_after_conflict=lambda: call_log.append("reload") or existing_run,
    )

    result = runtime.run()

    assert result is replayed_response
    assert call_log == [
        "build_record",
        ("create", running_record),
        "reload",
        ("recover_running", existing_run),
        ("recover", existing_run),
    ]


def test_assistant_turn_recovery_runtime_fails_when_conflict_run_disappears() -> None:
    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: None,
        recover_existing_running_turn=lambda value: None,
        recover_existing_turn=lambda value: value,
        build_running_turn_record=lambda: object(),
        create_run=lambda record: False,
        reload_existing_run_after_conflict=lambda: None,
    )

    with pytest.raises(
        ConfigurationError,
        match="Assistant turn run snapshot disappeared after create_run conflict",
    ):
        runtime.run()
