from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from app.modules.config_registry import ConfigLoader
from app.modules.project.infrastructure import ProjectDocumentFileStore
from app.modules.observability.service import AuditLogService, create_audit_log_service
from app.shared.runtime import (
    EXPORT_ROOT_DIR,
    LLMToolProvider,
    PROJECT_DOCUMENT_ROOT_DIR,
    SkillTemplateRenderer,
    ToolProvider,
)

from .project_incubator_service import ProjectIncubatorService
from .project_deletion_service import ProjectDeletionService
from .project_management_service import ProjectManagementService
from .project_service import ProjectService

if TYPE_CHECKING:
    from app.modules.content.service import StoryAssetService
    from app.modules.credential.service import CredentialService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_project_service() -> ProjectService:
    return ProjectService(document_file_store=ProjectDocumentFileStore(_default_project_document_root()))


def _default_export_root() -> Path:
    return Path(__file__).resolve().parents[4] / EXPORT_ROOT_DIR


def _default_project_document_root() -> Path:
    return Path(__file__).resolve().parents[4] / PROJECT_DOCUMENT_ROOT_DIR


def create_project_management_service(
    *,
    project_service: ProjectService | None = None,
    story_asset_service: StoryAssetService | None = None,
) -> ProjectManagementService:
    project_service_instance = project_service or create_project_service()
    if story_asset_service is None:
        from app.modules.content.service import create_story_asset_service

        story_asset_service = create_story_asset_service(project_service=project_service_instance)
    return ProjectManagementService(
        project_service=project_service_instance,
        story_asset_service=story_asset_service,
    )


def create_project_incubator_service(
    *,
    config_loader: ConfigLoader | None = None,
    credential_service_factory: Callable[[], CredentialService] | None = None,
    tool_provider: ToolProvider | None = None,
    template_renderer: SkillTemplateRenderer | None = None,
) -> ProjectIncubatorService:
    from app.modules.template.service import create_template_query_service
    from app.modules.credential.service import create_credential_service

    project_service = create_project_service()
    return ProjectIncubatorService(
        create_template_query_service(),
        create_project_management_service(project_service=project_service),
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        credential_service_factory=credential_service_factory
        or (lambda: create_credential_service(project_service=project_service)),
        tool_provider=tool_provider or LLMToolProvider(),
        template_renderer=template_renderer or SkillTemplateRenderer(),
    )


def create_project_deletion_service(
    *,
    project_service: ProjectService | None = None,
    audit_log_service: AuditLogService | None = None,
    export_root: Path | None = None,
    project_document_root: Path | None = None,
) -> ProjectDeletionService:
    return ProjectDeletionService(
        project_service=project_service or create_project_service(),
        audit_log_service=audit_log_service or create_audit_log_service(),
        export_root=export_root or _default_export_root(),
        project_document_root=project_document_root or _default_project_document_root(),
    )
