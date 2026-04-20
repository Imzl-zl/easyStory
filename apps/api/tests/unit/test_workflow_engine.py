from datetime import datetime, timezone

import pytest

from app.main import create_app
from app.modules.context.engine.context_builder import ContextBuilder
from app.modules.review.engine.review_executor import ReviewExecutor
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.modules.workflow.service.factory import create_workflow_service
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
    assert workflow.started_at is not None
    assert workflow.completed_at is None


def test_workflow_service_resume_clears_pause_fields(db) -> None:
    workflow = create_workflow(db, status="running", current_node_id="outline")
    service = create_workflow_service()

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
    assert workflow.started_at is not None
    assert workflow.completed_at is None


def test_workflow_service_resume_is_idempotent_for_running_state(db) -> None:
    started_at = datetime.now(timezone.utc)
    workflow = create_workflow(
        db,
        status="running",
        current_node_id="outline",
        started_at=started_at,
    )

    result = create_workflow_service().resume(workflow, current_node_id="chapter_gen")

    assert result is workflow
    assert workflow.status == "running"
    assert workflow.current_node_id == "outline"
    assert workflow.started_at == started_at.replace(tzinfo=None)


def test_workflow_service_cancel_is_idempotent_for_terminal_state(db) -> None:
    completed_at = datetime.now(timezone.utc)
    workflow = create_workflow(db, status="completed", completed_at=completed_at)

    result = create_workflow_service().cancel(workflow, current_node_id="chapter_gen")

    assert result is workflow
    assert workflow.status == "completed"
    assert workflow.current_node_id is None
    assert workflow.completed_at == completed_at.replace(tzinfo=None)


def test_workflow_engine_tracks_terminal_timestamp(db) -> None:
    workflow = create_workflow(db)
    service = create_workflow_service()

    service.start(workflow, current_node_id="outline")
    service.complete(workflow, current_node_id="export")

    assert workflow.status == "completed"
    assert workflow.current_node_id == "export"
    assert workflow.started_at is not None
    assert workflow.completed_at is not None


def test_workflow_engine_rejects_invalid_transition(db) -> None:
    workflow = create_workflow(db, status="completed")

    with pytest.raises(InvalidTransitionError):
        WorkflowEngine().transition(workflow, "running")


def test_runtime_components_live_in_expected_modules() -> None:
    assert WorkflowService.__module__ == "app.modules.workflow.service.workflow_service"
    assert WorkflowEngine.__module__ == "app.modules.workflow.engine.workflow_engine"
    assert ContextBuilder.__module__ == "app.modules.context.engine.context_builder"
    assert ReviewExecutor.__module__ == "app.modules.review.engine.review_executor"
