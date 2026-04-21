import pytest

from app.modules.workflow.service.workflow_app_start_runtime import (
    WorkflowAppStartRuntime,
)


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_workflow_app_start_runtime_runs_control_chain() -> None:
    call_log: list[object] = []
    workflow = type("Workflow", (), {"id": "workflow-1"})()

    runtime = WorkflowAppStartRuntime(
        resolve_workflow_config=lambda: call_log.append("config") or "workflow-config",
        ensure_preconditions=lambda: _return_async(call_log.append("preconditions")),
        build_execution=lambda workflow_config: call_log.append(("build", workflow_config)) or workflow,
        persist_started_workflow=lambda resolved_workflow, workflow_config: _return_async(
            call_log.append(("persist", resolved_workflow, workflow_config))
        ),
        dispatch_runtime=lambda execution_id: _return_async(call_log.append(("dispatch", execution_id))),
    )

    execution_id = await runtime.run()

    assert execution_id == "workflow-1"
    assert call_log == [
        "config",
        "preconditions",
        ("build", "workflow-config"),
        ("persist", workflow, "workflow-config"),
        ("dispatch", "workflow-1"),
    ]
