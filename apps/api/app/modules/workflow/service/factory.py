from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.project.service import ProjectService, create_project_service
from app.modules.workflow.engine import WorkflowEngine

from .chapter_task_service import ChapterTaskService
from .workflow_app_service import WorkflowAppService
from .workflow_service import WorkflowService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_workflow_service(
    *,
    engine: WorkflowEngine | None = None,
) -> WorkflowService:
    return WorkflowService(engine or WorkflowEngine())


def create_workflow_app_service(
    *,
    workflow_service: WorkflowService | None = None,
    project_service: ProjectService | None = None,
    config_loader: ConfigLoader | None = None,
) -> WorkflowAppService:
    return WorkflowAppService(
        workflow_service=workflow_service or create_workflow_service(),
        project_service=project_service or create_project_service(),
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
    )


def create_chapter_task_service(
    *,
    project_service: ProjectService | None = None,
) -> ChapterTaskService:
    return ChapterTaskService(project_service or create_project_service())
