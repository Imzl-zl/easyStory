import pytest

from app.modules.assistant.service.turn.assistant_turn_prepare_runtime import (
    LangGraphAssistantTurnPrepareRuntime,
)


@pytest.mark.asyncio
async def test_assistant_turn_prepare_runtime_runs_prepare_and_recover_successfully() -> None:
    call_log: list[object] = []
    resolved_hooks = ["hook.one"]
    prepared = object()
    replayed_response = object()

    async def prepare_turn(hooks):
        call_log.append(("prepare", list(hooks)))
        return prepared

    async def run_prepare_on_error_hooks(hooks, error: Exception):
        call_log.append(("prepare_on_error", list(hooks), error))
        return None

    runtime = LangGraphAssistantTurnPrepareRuntime(
        resolve_hooks=lambda: call_log.append("resolve_hooks") or list(resolved_hooks),
        prepare_turn=prepare_turn,
        run_prepare_on_error_hooks=run_prepare_on_error_hooks,
        recover_or_start_turn=lambda value: call_log.append(("recover", value)) or replayed_response,
    )

    result = await runtime.run()

    assert result.resolved_hooks == resolved_hooks
    assert result.prepared is prepared
    assert result.replayed_response is replayed_response
    assert call_log == [
        "resolve_hooks",
        ("prepare", resolved_hooks),
        ("recover", prepared),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_prepare_runtime_runs_prepare_on_error_hooks_for_prepare_failure() -> None:
    call_log: list[object] = []
    original_error = RuntimeError("prepare failed")

    async def prepare_turn(hooks):
        call_log.append(("prepare", list(hooks)))
        raise original_error

    async def run_prepare_on_error_hooks(hooks, error: Exception):
        call_log.append(("prepare_on_error", list(hooks), error))
        return None

    runtime = LangGraphAssistantTurnPrepareRuntime(
        resolve_hooks=lambda: ["hook.one"],
        prepare_turn=prepare_turn,
        run_prepare_on_error_hooks=run_prepare_on_error_hooks,
        recover_or_start_turn=lambda prepared: prepared,
    )

    with pytest.raises(RuntimeError, match="prepare failed"):
        await runtime.run()

    assert call_log == [
        ("prepare", ["hook.one"]),
        ("prepare_on_error", ["hook.one"], original_error),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_prepare_runtime_uses_hook_error_when_prepare_on_error_fails() -> None:
    original_error = RuntimeError("prepare failed")
    hook_error = ValueError("hook failed")

    async def prepare_turn(hooks):
        raise original_error

    async def run_prepare_on_error_hooks(hooks, error: Exception):
        assert hooks == []
        assert error is original_error
        return hook_error

    runtime = LangGraphAssistantTurnPrepareRuntime(
        resolve_hooks=lambda: (_ for _ in ()).throw(original_error),
        prepare_turn=prepare_turn,
        run_prepare_on_error_hooks=run_prepare_on_error_hooks,
        recover_or_start_turn=lambda prepared: prepared,
    )

    with pytest.raises(ValueError, match="hook failed"):
        await runtime.run()


@pytest.mark.asyncio
async def test_assistant_turn_prepare_runtime_does_not_run_prepare_on_error_hooks_for_recover_failure() -> None:
    call_log: list[object] = []
    recover_error = RuntimeError("recover failed")

    async def prepare_turn(hooks):
        call_log.append(("prepare", list(hooks)))
        return object()

    async def run_prepare_on_error_hooks(hooks, error: Exception):
        call_log.append(("prepare_on_error", list(hooks), error))
        return None

    def recover_or_start_turn(prepared):
        call_log.append(("recover", prepared))
        raise recover_error

    runtime = LangGraphAssistantTurnPrepareRuntime(
        resolve_hooks=lambda: ["hook.one"],
        prepare_turn=prepare_turn,
        run_prepare_on_error_hooks=run_prepare_on_error_hooks,
        recover_or_start_turn=recover_or_start_turn,
    )

    with pytest.raises(RuntimeError, match="recover failed"):
        await runtime.run()

    assert len(call_log) == 2
    assert call_log[0] == ("prepare", ["hook.one"])
    assert call_log[1][0] == "recover"
