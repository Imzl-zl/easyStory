import pytest

from app.modules.assistant.service.turn.assistant_turn_execution_runtime import (
    AssistantTurnExecutionRuntime,
)


@pytest.mark.asyncio
async def test_assistant_turn_execution_runtime_runs_success_path_and_stores_response() -> None:
    call_log: list[object] = []
    raw_output = {"content": "hello"}
    response = object()

    async def run_before_hooks():
        call_log.append("before")
        return ["before-result"]

    async def call_turn_llm():
        call_log.append("llm")
        return raw_output

    async def finalize_response(before_results, llm_raw_output):
        call_log.append(("finalize", before_results, llm_raw_output))
        return response

    async def run_prepared_on_error_hooks(error: Exception):
        call_log.append(("error_hook", error))
        return None

    async def store_terminal_turn(*, response=None, error=None):
        call_log.append(("store", response, error))

    runtime = AssistantTurnExecutionRuntime(
        run_before_hooks=run_before_hooks,
        call_turn_llm=call_turn_llm,
        finalize_response=finalize_response,
        run_prepared_on_error_hooks=run_prepared_on_error_hooks,
        store_terminal_turn=store_terminal_turn,
    )

    result = await runtime.run()

    assert result is response
    assert call_log == [
        "before",
        "llm",
        ("finalize", ["before-result"], raw_output),
        ("store", response, None),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_execution_runtime_store_failure_does_not_trigger_error_hooks() -> None:
    call_log: list[object] = []
    store_error = RuntimeError("store failed")

    async def run_before_hooks():
        call_log.append("before")
        return []

    async def call_turn_llm():
        call_log.append("llm")
        return {"content": "hello"}

    async def finalize_response(before_results, llm_raw_output):
        call_log.append(("finalize", before_results, llm_raw_output))
        return {"content": "done"}

    async def run_prepared_on_error_hooks(error: Exception):
        call_log.append(("error_hook", error))
        return None

    async def store_terminal_turn(*, response=None, error=None):
        call_log.append(("store", response, error))
        raise store_error

    runtime = AssistantTurnExecutionRuntime(
        run_before_hooks=run_before_hooks,
        call_turn_llm=call_turn_llm,
        finalize_response=finalize_response,
        run_prepared_on_error_hooks=run_prepared_on_error_hooks,
        store_terminal_turn=store_terminal_turn,
    )

    with pytest.raises(RuntimeError, match="store failed"):
        await runtime.run()

    assert ("error_hook", store_error) not in call_log


@pytest.mark.asyncio
async def test_assistant_turn_execution_runtime_uses_hook_error_for_terminal_store() -> None:
    call_log: list[object] = []
    execution_error = RuntimeError("llm failed")
    hook_error = ValueError("hook failed")

    async def run_before_hooks():
        call_log.append("before")
        return []

    async def call_turn_llm():
        call_log.append("llm")
        raise execution_error

    async def finalize_response(before_results, llm_raw_output):
        raise AssertionError("finalize should not run")

    async def run_prepared_on_error_hooks(error: Exception):
        call_log.append(("error_hook", error))
        return hook_error

    async def store_terminal_turn(*, response=None, error=None):
        call_log.append(("store", response, error))

    runtime = AssistantTurnExecutionRuntime(
        run_before_hooks=run_before_hooks,
        call_turn_llm=call_turn_llm,
        finalize_response=finalize_response,
        run_prepared_on_error_hooks=run_prepared_on_error_hooks,
        store_terminal_turn=store_terminal_turn,
    )

    with pytest.raises(ValueError, match="hook failed"):
        await runtime.run()

    assert call_log == [
        "before",
        "llm",
        ("error_hook", execution_error),
        ("store", None, hook_error),
    ]
