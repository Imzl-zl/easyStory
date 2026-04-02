from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AUDIT_ENTITY_MODEL_CREDENTIAL, AuditLogService
from app.modules.project.service import ProjectService

from .credential_query_support import require_actor_credential
from .credential_view_support import to_view
from .dto import CredentialViewDTO


def record_audit(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    event_type: str,
    credential: ModelCredential,
    details: dict | None,
    audit_log_service: AuditLogService,
) -> None:
    payload = {
        "provider": credential.provider,
        "owner_type": credential.owner_type,
        "owner_id": str(credential.owner_id) if credential.owner_id is not None else None,
    }
    if details:
        payload.update(details)
    audit_log_service.record(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=AUDIT_ENTITY_MODEL_CREDENTIAL,
        entity_id=credential.id,
        details=payload,
    )


async def set_active_state(
    db: AsyncSession,
    credential_id: uuid.UUID,
    *,
    actor_user_id: uuid.UUID,
    is_active: bool,
    event_type: str,
    project_service: ProjectService,
    audit_log_service: AuditLogService,
    decrypt_api_key: Callable[[str], str],
) -> CredentialViewDTO:
    credential = await require_actor_credential(
        db,
        credential_id,
        actor_user_id=actor_user_id,
        project_service=project_service,
    )
    if credential.is_active == is_active:
        return to_view(credential, decrypt_api_key=decrypt_api_key)
    credential.is_active = is_active
    record_audit(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        credential=credential,
        details=None,
        audit_log_service=audit_log_service,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return to_view(credential, decrypt_api_key=decrypt_api_key)
