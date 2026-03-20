from __future__ import annotations

from .audit_log_service import AuditLogService


def create_audit_log_service() -> AuditLogService:
    return AuditLogService()
