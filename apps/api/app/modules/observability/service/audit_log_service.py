from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.observability.models import AuditLog

AUDIT_ENTITY_MODEL_CREDENTIAL = "model_credential"
AUDIT_ENTITY_PROJECT = "project"


class AuditLogService:
    def record(
        self,
        db: Session,
        *,
        actor_user_id: uuid.UUID | None,
        event_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        details: dict | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        db.add(audit_log)
        return audit_log
