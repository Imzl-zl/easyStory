import pytest

from app.modules.workflow.service.workflow_hook_event_runtime import (
    LangGraphWorkflowHookEventRuntime,
)


@pytest.mark.asyncio
async def test_workflow_hook_event_runtime_records_skip_and_success() -> None:
    call_log: list[object] = []
    hooks = ["hook.skip", "hook.run"]

    runtime = LangGraphWorkflowHookEventRuntime(
        resolve_hooks=lambda: call_log.append("resolve_hooks") or hooks,
        matches_condition=lambda hook: hook != "hook.skip",
        record_skip=lambda hook: call_log.append(("skip", hook)),
        execute_hook=lambda hook: _return_async(call_log.append(("execute", hook)) or f"result:{hook}"),
        record_success=lambda hook, result: call_log.append(("success", hook, result)),
    )

    result = await runtime.run()

    assert result == ["result:hook.run"]
    assert call_log == [
        "resolve_hooks",
        ("skip", "hook.skip"),
        ("execute", "hook.run"),
        ("success", "hook.run", "result:hook.run"),
    ]


@pytest.mark.asyncio
async def test_workflow_hook_event_runtime_returns_empty_results_without_hooks() -> None:
    runtime = LangGraphWorkflowHookEventRuntime(
        resolve_hooks=lambda: [],
        matches_condition=lambda hook: True,
        record_skip=lambda hook: None,
        execute_hook=lambda hook: _return_async(hook),
        record_success=lambda hook, result: None,
    )

    assert await runtime.run() == []


async def _return_async(value):
    return value
