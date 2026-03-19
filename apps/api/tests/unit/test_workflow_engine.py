from app.main import create_app
from app.modules.context.engine.context_builder import ContextBuilder
from app.modules.review.engine.review_executor import ReviewExecutor
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.modules.workflow.service.workflow_service import WorkflowService


def test_app_registers_health_route() -> None:
    app = create_app()

    assert any(getattr(route, "path", None) == "/healthz" for route in app.routes)


def test_runtime_placeholders_live_in_modules() -> None:
    assert WorkflowService.__module__ == "app.modules.workflow.service.workflow_service"
    assert WorkflowEngine.__module__ == "app.modules.workflow.engine.workflow_engine"
    assert ContextBuilder.__module__ == "app.modules.context.engine.context_builder"
    assert ReviewExecutor.__module__ == "app.modules.review.engine.review_executor"
