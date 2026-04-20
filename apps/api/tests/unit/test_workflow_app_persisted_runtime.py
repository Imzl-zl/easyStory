from types import SimpleNamespace

import pytest

from app.modules.workflow.service.workflow_app_persisted_runtime import (
    LangGraphWorkflowAppPersistedRuntime,
)
from app.shared.runtime.errors import BusinessRuleError


@pytest.mark.asyncio
async def test_workflow_app_persisted_runtime_runs_success_path() -> None:
    call_log: list[object] = []
    workflow = SimpleNamespace(current_node_id="chapter_split")

    runtime = LangGraphWorkflowAppPersistedRuntime(
        load_workflow=lambda: _return_async(call_log.append("load") or workflow),
        run_runtime=lambda loaded_workflow: _return_async(call_log.append(("run", loaded_workflow))),
        commit=lambda: _return_async(call_log.append("commit")),
        recover_runtime_failure=lambda current_node_id, detail, reason: _return_async(
            call_log.append(("recover", current_node_id, detail, reason))
        ),
    )

    await runtime.run()

    assert call_log == [
        "load",
        ("run", workflow),
        "commit",
    ]


@pytest.mark.asyncio
async def test_workflow_app_persisted_runtime_recovers_business_rule_failure_without_error_reason() -> None:
    call_log: list[object] = []
    workflow = SimpleNamespace(current_node_id="chapter_gen")
    failure = BusinessRuleError("业务失败")

    async def run_runtime(loaded_workflow):
        raise failure

    runtime = LangGraphWorkflowAppPersistedRuntime(
        load_workflow=lambda: _return_async(workflow),
        run_runtime=run_runtime,
        commit=lambda: _return_async(None),
        recover_runtime_failure=lambda current_node_id, detail, reason: _return_async(
            call_log.append((current_node_id, detail, reason))
        ),
    )

    with pytest.raises(BusinessRuleError, match="业务失败"):
        await runtime.run()

    assert call_log == [("chapter_gen", "业务失败", None)]


@pytest.mark.asyncio
async def test_workflow_app_persisted_runtime_recovers_generic_failure_with_error_reason() -> None:
    call_log: list[object] = []
    workflow = SimpleNamespace(current_node_id="chapter_gen")

    async def run_runtime(loaded_workflow):
        raise RuntimeError("boom")

    runtime = LangGraphWorkflowAppPersistedRuntime(
        load_workflow=lambda: _return_async(workflow),
        run_runtime=run_runtime,
        commit=lambda: _return_async(None),
        recover_runtime_failure=lambda current_node_id, detail, reason: _return_async(
            call_log.append((current_node_id, detail, reason))
        ),
    )

    with pytest.raises(RuntimeError, match="boom"):
        await runtime.run()

    assert call_log == [("chapter_gen", "boom", "error")]


async def _return_async(value):
    return value
