from __future__ import annotations

import uuid

from sqlalchemy import select

from app.modules.observability.models import AuditLog
from app.shared.runtime.errors import BusinessRuleError

from .audit_log_service import AUDIT_ENTITY_MODEL_CREDENTIAL, AUDIT_ENTITY_PROJECT
from .dto import AuditLogViewDTO

EVENT_TYPE_BLANK_MESSAGE = "event_type filter cannot be blank"


def normalize_event_type_filter(event_type: str | None) -> str | None:
    if event_type is None:
        return None
    normalized = event_type.strip()
    if not normalized:
        raise BusinessRuleError(EVENT_TYPE_BLANK_MESSAGE)
    return normalized


def build_project_audit_log_statement(
    project_id: uuid.UUID,
    *,
    event_type: str | None,
):
    statement = select(AuditLog).where(
        AuditLog.entity_type == AUDIT_ENTITY_PROJECT,
        AuditLog.entity_id == project_id,
    )
    if event_type is not None:
        statement = statement.where(AuditLog.event_type == event_type)
    return statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())


def build_credential_audit_log_statement(
    credential_id: uuid.UUID,
    *,
    event_type: str | None,
):
    statement = select(AuditLog).where(
        AuditLog.entity_type == AUDIT_ENTITY_MODEL_CREDENTIAL,
        AuditLog.entity_id == credential_id,
    )
    if event_type is not None:
        statement = statement.where(AuditLog.event_type == event_type)
    return statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())


def to_audit_log_view(audit_log: AuditLog) -> AuditLogViewDTO:
    details = audit_log.details if isinstance(audit_log.details, dict) else None
    return AuditLogViewDTO(
        id=audit_log.id,
        actor_user_id=audit_log.actor_user_id,
        event_type=audit_log.event_type,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        details=details,  # type: ignore[arg-type]
        created_at=audit_log.created_at,
    )
