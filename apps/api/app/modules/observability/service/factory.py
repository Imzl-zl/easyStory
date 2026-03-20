from __future__ import annotations

from .audit_log_service import AuditLogService
from .workflow_observability_service import WorkflowObservabilityService


def create_audit_log_service() -> AuditLogService:
    return AuditLogService()


def create_workflow_observability_service() -> WorkflowObservabilityService:
    return WorkflowObservabilityService()
