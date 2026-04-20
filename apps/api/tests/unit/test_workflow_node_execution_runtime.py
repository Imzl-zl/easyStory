import pytest

from app.modules.workflow.service.workflow_node_execution_runtime import (
    LangGraphWorkflowNodeExecutionRuntime,
)
from app.modules.workflow.service.workflow_runtime_shared import NodeOutcome


@pytest.mark.asyncio
async def test_workflow_node_execution_runtime_runs_success_path() -> None:
    call_log: list[object] = []
    outcome = NodeOutcome(next_node_id="chapter_gen")

    async def run_before_hook():
        call_log.append("before")

    async def run_before_on_error(error: Exception):
        call_log.append(("before_on_error", error))

    async def dispatch_node():
        call_log.append("dispatch")
        return outcome

    async def run_dispatch_on_error(error: Exception):
        call_log.append(("dispatch_on_error", error))

    async def run_after_hook(resolved_outcome: NodeOutcome):
        call_log.append(("after", resolved_outcome))

    async def run_after_on_error(resolved_outcome: NodeOutcome, error: Exception):
        call_log.append(("after_on_error", resolved_outcome, error))

    runtime = LangGraphWorkflowNodeExecutionRuntime(
        run_before_hook=run_before_hook,
        run_before_on_error=run_before_on_error,
        dispatch_node=dispatch_node,
        run_dispatch_on_error=run_dispatch_on_error,
        run_after_hook=run_after_hook,
        run_after_on_error=run_after_on_error,
    )

    result = await runtime.run()

    assert result == outcome
    assert call_log == [
        "before",
        "dispatch",
        ("after", outcome),
    ]


@pytest.mark.asyncio
async def test_workflow_node_execution_runtime_runs_on_error_for_before_failure() -> None:
    call_log: list[object] = []
    failure = RuntimeError("before failed")

    async def run_before_hook():
        raise failure

    async def run_before_on_error(error: Exception):
        call_log.append(("before_on_error", error))

    runtime = LangGraphWorkflowNodeExecutionRuntime(
        run_before_hook=run_before_hook,
        run_before_on_error=run_before_on_error,
        dispatch_node=lambda: _return_async(NodeOutcome(next_node_id="chapter_gen")),
        run_dispatch_on_error=lambda error: _return_async(None),
        run_after_hook=lambda outcome: _return_async(None),
        run_after_on_error=lambda outcome, error: _return_async(None),
    )

    with pytest.raises(RuntimeError, match="before failed"):
        await runtime.run()

    assert call_log == [("before_on_error", failure)]


@pytest.mark.asyncio
async def test_workflow_node_execution_runtime_runs_on_error_for_dispatch_failure() -> None:
    call_log: list[object] = []
    failure = RuntimeError("dispatch failed")

    async def dispatch_node():
        raise failure

    async def run_dispatch_on_error(error: Exception):
        call_log.append(("dispatch_on_error", error))

    runtime = LangGraphWorkflowNodeExecutionRuntime(
        run_before_hook=lambda: _return_async(None),
        run_before_on_error=lambda error: _return_async(None),
        dispatch_node=dispatch_node,
        run_dispatch_on_error=run_dispatch_on_error,
        run_after_hook=lambda outcome: _return_async(None),
        run_after_on_error=lambda outcome, error: _return_async(None),
    )

    with pytest.raises(RuntimeError, match="dispatch failed"):
        await runtime.run()

    assert call_log == [("dispatch_on_error", failure)]


@pytest.mark.asyncio
async def test_workflow_node_execution_runtime_runs_on_error_for_after_failure() -> None:
    call_log: list[object] = []
    outcome = NodeOutcome(next_node_id="chapter_gen")
    failure = RuntimeError("after failed")

    async def run_after_hook(resolved_outcome: NodeOutcome):
        assert resolved_outcome == outcome
        raise failure

    async def run_after_on_error(resolved_outcome: NodeOutcome, error: Exception):
        call_log.append(("after_on_error", resolved_outcome, error))

    runtime = LangGraphWorkflowNodeExecutionRuntime(
        run_before_hook=lambda: _return_async(None),
        run_before_on_error=lambda error: _return_async(None),
        dispatch_node=lambda: _return_async(outcome),
        run_dispatch_on_error=lambda error: _return_async(None),
        run_after_hook=run_after_hook,
        run_after_on_error=run_after_on_error,
    )

    with pytest.raises(RuntimeError, match="after failed"):
        await runtime.run()

    assert call_log == [("after_on_error", outcome, failure)]


async def _return_async(value):
    return value
