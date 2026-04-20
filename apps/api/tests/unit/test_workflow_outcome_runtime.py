from types import SimpleNamespace
import uuid

from app.modules.workflow.service.workflow_outcome_runtime import LangGraphWorkflowOutcomeRuntime
from app.modules.workflow.service.workflow_runtime_shared import NodeOutcome


class _FakeWorkflowService:
    def fail(self, workflow, *, current_node_id: str | None = None):
        workflow.status = "failed"
        workflow.current_node_id = current_node_id
        return workflow

    def pause(
        self,
        workflow,
        *,
        reason: str | None,
        current_node_id: str | None = None,
        resume_from_node: str | None = None,
    ):
        workflow.status = "paused"
        workflow.current_node_id = current_node_id
        workflow.pause_reason = reason
        workflow.resume_from_node = resume_from_node or current_node_id
        return workflow

    def complete(self, workflow, *, current_node_id: str | None = None):
        workflow.status = "completed"
        workflow.current_node_id = current_node_id
        workflow.pause_reason = None
        workflow.resume_from_node = None
        return workflow


def _build_workflow():
    return SimpleNamespace(
        id=uuid.uuid4(),
        status="running",
        current_node_id="chapter_split",
        pause_reason=None,
        resume_from_node=None,
        snapshot=None,
    )


def _build_node():
    return SimpleNamespace(id="chapter_gen")


def test_workflow_outcome_runtime_applies_failed_outcome() -> None:
    workflow = _build_workflow()
    logs: list[dict] = []
    outcome = NodeOutcome(
        next_node_id="chapter_gen",
        workflow_status="failed",
        snapshot_extra={"current_node_execution_id": "exec-1"},
    )

    runtime = LangGraphWorkflowOutcomeRuntime(
        workflow_service=_FakeWorkflowService(),
        record_execution_log=lambda db, **kwargs: logs.append(kwargs),
        db=None,
        workflow=workflow,
        node=_build_node(),
        outcome=outcome,
    )

    terminated = runtime.run()

    assert terminated is True
    assert workflow.status == "failed"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.snapshot["current_node_execution_id"] == "exec-1"
    assert logs == [
        {
            "workflow_execution_id": workflow.id,
            "node_execution_id": None,
            "level": "ERROR",
            "message": "Workflow failed",
            "details": {"node_id": "chapter_gen"},
        }
    ]


def test_workflow_outcome_runtime_applies_paused_outcome() -> None:
    workflow = _build_workflow()
    logs: list[dict] = []
    outcome = NodeOutcome(
        next_node_id="chapter_gen",
        pause_reason="review_failed",
        snapshot_extra={"current_node_execution_id": "exec-1"},
    )

    runtime = LangGraphWorkflowOutcomeRuntime(
        workflow_service=_FakeWorkflowService(),
        record_execution_log=lambda db, **kwargs: logs.append(kwargs),
        db=None,
        workflow=workflow,
        node=_build_node(),
        outcome=outcome,
    )

    terminated = runtime.run()

    assert terminated is True
    assert workflow.status == "paused"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.resume_from_node == "chapter_gen"
    assert workflow.pause_reason == "review_failed"
    assert workflow.snapshot["current_node_execution_id"] == "exec-1"
    assert logs == [
        {
            "workflow_execution_id": workflow.id,
            "node_execution_id": None,
            "level": "WARNING",
            "message": "Workflow paused",
            "details": {"node_id": "chapter_gen", "reason": "review_failed"},
        }
    ]


def test_workflow_outcome_runtime_applies_completed_outcome() -> None:
    workflow = _build_workflow()
    workflow.snapshot = {"old": True}
    logs: list[dict] = []
    outcome = NodeOutcome(next_node_id=None)

    runtime = LangGraphWorkflowOutcomeRuntime(
        workflow_service=_FakeWorkflowService(),
        record_execution_log=lambda db, **kwargs: logs.append(kwargs),
        db=None,
        workflow=workflow,
        node=_build_node(),
        outcome=outcome,
    )

    terminated = runtime.run()

    assert terminated is True
    assert workflow.status == "completed"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.snapshot is None
    assert logs == [
        {
            "workflow_execution_id": workflow.id,
            "node_execution_id": None,
            "level": "INFO",
            "message": "Workflow completed",
            "details": {"node_id": "chapter_gen"},
        }
    ]


def test_workflow_outcome_runtime_applies_continue_outcome() -> None:
    workflow = _build_workflow()
    workflow.snapshot = {"old": True}
    logs: list[dict] = []
    outcome = NodeOutcome(next_node_id="export")

    runtime = LangGraphWorkflowOutcomeRuntime(
        workflow_service=_FakeWorkflowService(),
        record_execution_log=lambda db, **kwargs: logs.append(kwargs),
        db=None,
        workflow=workflow,
        node=_build_node(),
        outcome=outcome,
    )

    terminated = runtime.run()

    assert terminated is False
    assert workflow.status == "running"
    assert workflow.current_node_id == "export"
    assert workflow.snapshot is None
    assert logs == []
