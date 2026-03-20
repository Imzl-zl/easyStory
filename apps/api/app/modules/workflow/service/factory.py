from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.content.service import create_chapter_content_service
from app.modules.context.engine import create_context_builder
from app.modules.credential.service import create_credential_service
from app.modules.export.service import create_export_service
from app.modules.project.service import ProjectService, create_project_service
from app.modules.workflow.engine import WorkflowEngine
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer

from .chapter_task_service import ChapterTaskService
from .workflow_app_service import WorkflowAppService
from .workflow_runtime_service import WorkflowRuntimeService
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
    runtime_service: WorkflowRuntimeService | None = None,
) -> WorkflowAppService:
    resolved_workflow_service = workflow_service or create_workflow_service()
    return WorkflowAppService(
        workflow_service=resolved_workflow_service,
        project_service=project_service or create_project_service(),
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        runtime_service=runtime_service or create_workflow_runtime_service(
            workflow_service=resolved_workflow_service
        ),
    )


def create_chapter_task_service(
    *,
    project_service: ProjectService | None = None,
) -> ChapterTaskService:
    return ChapterTaskService(project_service or create_project_service())


def create_workflow_runtime_service(
    *,
    workflow_service: WorkflowService | None = None,
    tool_provider: LLMToolProvider | None = None,
) -> WorkflowRuntimeService:
    return WorkflowRuntimeService(
        workflow_service=workflow_service or create_workflow_service(),
        chapter_content_service=create_chapter_content_service(),
        context_builder=create_context_builder(),
        credential_service_factory=create_credential_service,
        export_service=create_export_service(),
        template_renderer=SkillTemplateRenderer(),
        tool_provider=tool_provider or LLMToolProvider(),
    )
