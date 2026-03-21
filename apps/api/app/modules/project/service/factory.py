from __future__ import annotations

from pathlib import Path

from app.modules.export.service import EXPORT_ROOT_DIR
from app.modules.observability.service import AuditLogService, create_audit_log_service

from .project_deletion_service import ProjectDeletionService
from .project_management_service import ProjectManagementService
from .project_service import ProjectService


def create_project_service() -> ProjectService:
    return ProjectService()


def _default_export_root() -> Path:
    return Path(__file__).resolve().parents[4] / EXPORT_ROOT_DIR


def create_project_management_service(
    *,
    project_service: ProjectService | None = None,
) -> ProjectManagementService:
    return ProjectManagementService(project_service=project_service or create_project_service())


def create_project_deletion_service(
    *,
    project_service: ProjectService | None = None,
    audit_log_service: AuditLogService | None = None,
    export_root: Path | None = None,
) -> ProjectDeletionService:
    return ProjectDeletionService(
        project_service=project_service or create_project_service(),
        audit_log_service=audit_log_service or create_audit_log_service(),
        export_root=export_root or _default_export_root(),
    )
