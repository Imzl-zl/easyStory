import pytest

from app.main import create_app
from app.modules.context.engine.context_builder import ContextBuilder
from app.modules.review.engine.review_executor import ReviewExecutor
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.modules.workflow.service.workflow_service import WorkflowService
from app.modules.workflow.engine import InvalidTransitionError
from tests.unit.models.helpers import create_workflow


def test_app_registers_health_route() -> None:
    app = create_app()

    assert any(getattr(route, "path", None) == "/healthz" for route in app.routes)


def test_workflow_engine_applies_pause_transition(db) -> None:
    workflow = create_workflow(db)
    engine = WorkflowEngine()

    engine.transition(workflow, "running", current_node_id="outline")
    engine.transition(
        workflow,
        "paused",
        current_node_id="chapter_gen",
        pause_reason="review_failed",
        resume_from_node="chapter_gen",
    )

    assert workflow.status == "paused"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.pause_reason == "review_failed"
    assert workflow.resume_from_node == "chapter_gen"


def test_workflow_service_resume_clears_pause_fields(db) -> None:
    workflow = create_workflow(db, status="running", current_node_id="outline")
    service = WorkflowService()

    service.pause(
        workflow,
        reason="user_request",
        current_node_id="chapter_gen",
        resume_from_node="chapter_gen",
    )
    service.resume(workflow)

    assert workflow.status == "running"
    assert workflow.current_node_id == "chapter_gen"
    assert workflow.pause_reason is None
    assert workflow.resume_from_node is None


def test_workflow_engine_rejects_invalid_transition(db) -> None:
    workflow = create_workflow(db, status="completed")

    with pytest.raises(InvalidTransitionError):
        WorkflowEngine().transition(workflow, "running")


def test_runtime_components_live_in_expected_modules() -> None:
    assert WorkflowService.__module__ == "app.modules.workflow.service.workflow_service"
    assert WorkflowEngine.__module__ == "app.modules.workflow.engine.workflow_engine"
    assert ContextBuilder.__module__ == "app.modules.context.engine.context_builder"
    assert ReviewExecutor.__module__ == "app.modules.review.engine.review_executor"
