from __future__ import annotations

from app.modules.observability.service import AuditLogService, create_audit_log_service

from .project_management_service import ProjectManagementService
from .project_service import ProjectService


def create_project_service() -> ProjectService:
    return ProjectService()


def create_project_management_service(
    *,
    project_service: ProjectService | None = None,
    audit_log_service: AuditLogService | None = None,
) -> ProjectManagementService:
    return ProjectManagementService(
        project_service=project_service or create_project_service(),
        audit_log_service=audit_log_service or create_audit_log_service(),
    )
