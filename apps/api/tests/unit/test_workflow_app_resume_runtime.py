import pytest

from app.modules.workflow.service.workflow_app_resume_runtime import (
    LangGraphWorkflowAppResumeRuntime,
)


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_workflow_app_resume_runtime_runs_control_chain() -> None:
    call_log: list[object] = []
    workflow = type("Workflow", (), {"id": "workflow-1"})()

    runtime = LangGraphWorkflowAppResumeRuntime(
        ensure_resume_allowed=lambda: _return_async(call_log.append("resume_allowed")),
        resume_workflow=lambda: _return_async(call_log.append("resume") or workflow),
        dispatch_runtime=lambda execution_id: _return_async(call_log.append(("dispatch", execution_id))),
    )

    execution_id = await runtime.run()

    assert execution_id == "workflow-1"
    assert call_log == [
        "resume_allowed",
        "resume",
        ("dispatch", "workflow-1"),
    ]
