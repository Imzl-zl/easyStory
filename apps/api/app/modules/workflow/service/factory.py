from __future__ import annotations

from app.modules.workflow.engine import WorkflowEngine

from .workflow_service import WorkflowService


def create_workflow_service(
    *,
    engine: WorkflowEngine | None = None,
) -> WorkflowService:
    return WorkflowService(engine or WorkflowEngine())
