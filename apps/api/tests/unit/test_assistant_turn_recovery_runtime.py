import pytest

from app.modules.assistant.service.turn.assistant_turn_recovery_runtime import (
    LangGraphAssistantTurnRecoveryRuntime,
)
from app.shared.runtime.errors import ConfigurationError


@pytest.mark.asyncio
async def test_assistant_turn_recovery_runtime_recovers_existing_run() -> None:
    call_log: list[object] = []
    existing_run = object()
    replayed_response = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: _return_async(existing_run),
        recover_existing_running_turn=lambda value: _return_async(
            call_log.append(("recover_running", value))
        ),
        recover_existing_turn=lambda value: call_log.append(("recover", value)) or replayed_response,
        build_running_turn_record=lambda: (_ for _ in ()).throw(
            AssertionError("should not build record")
        ),
        create_run=lambda record: _fail_async("should not create run"),
        reload_existing_run_after_conflict=lambda: _fail_async("should not reload conflict"),
    )

    result = await runtime.run()

    assert result is replayed_response
    assert call_log == [
        ("recover_running", existing_run),
        ("recover", existing_run),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_recovery_runtime_creates_new_run_without_replay() -> None:
    call_log: list[object] = []
    running_record = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: _return_async(None),
        recover_existing_running_turn=lambda value: _return_async(
            call_log.append(("recover_running", value))
        ),
        recover_existing_turn=lambda value: call_log.append(("recover", value)),
        build_running_turn_record=lambda: call_log.append("build_record") or running_record,
        create_run=lambda record: _return_async(call_log.append(("create", record)) or True),
        reload_existing_run_after_conflict=lambda: _return_async(call_log.append("reload")),
    )

    result = await runtime.run()

    assert result is None
    assert call_log == [
        "build_record",
        ("create", running_record),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_recovery_runtime_recovers_after_create_conflict() -> None:
    call_log: list[object] = []
    running_record = object()
    existing_run = object()
    replayed_response = object()

    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: _return_async(None),
        recover_existing_running_turn=lambda value: _return_async(
            call_log.append(("recover_running", value))
        ),
        recover_existing_turn=lambda value: call_log.append(("recover", value)) or replayed_response,
        build_running_turn_record=lambda: call_log.append("build_record") or running_record,
        create_run=lambda record: _return_async(call_log.append(("create", record)) or False),
        reload_existing_run_after_conflict=lambda: _return_async(
            call_log.append("reload") or existing_run
        ),
    )

    result = await runtime.run()

    assert result is replayed_response
    assert call_log == [
        "build_record",
        ("create", running_record),
        "reload",
        ("recover_running", existing_run),
        ("recover", existing_run),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_recovery_runtime_fails_when_conflict_run_disappears() -> None:
    runtime = LangGraphAssistantTurnRecoveryRuntime(
        resolve_existing_run=lambda: _return_async(None),
        recover_existing_running_turn=lambda value: _return_async(None),
        recover_existing_turn=lambda value: value,
        build_running_turn_record=lambda: object(),
        create_run=lambda record: _return_async(False),
        reload_existing_run_after_conflict=lambda: _return_async(None),
    )

    with pytest.raises(
        ConfigurationError,
        match="Assistant turn run snapshot disappeared after create_run conflict",
    ):
        await runtime.run()


async def _return_async(value):
    return value


async def _fail_async(message: str):
    raise AssertionError(message)
