from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.infrastructure import AsyncCredentialVerifier
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AuditLogService

from .credential_mutation_support import record_audit
from .credential_service_support import to_verify_result
from .dto import CredentialVerifyResultDTO


async def verify_credential_record(
    db: AsyncSession,
    *,
    credential: ModelCredential,
    verifier: AsyncCredentialVerifier,
    decrypt_api_key,
    actor_user_id: uuid.UUID,
    event_type: str,
    audit_log_service: AuditLogService,
) -> CredentialVerifyResultDTO:
    api_key = decrypt_api_key(credential.encrypted_key)
    try:
        result = await verifier.verify(
            provider=credential.provider,
            api_key=api_key,
            base_url=credential.base_url,
            api_dialect=credential.api_dialect,
            default_model=credential.default_model or "",
        )
    except Exception as exc:
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            credential=credential,
            details={"status": "failed", "error": str(exc)},
            audit_log_service=audit_log_service,
        )
        await db.commit()
        raise
    credential.last_verified_at = result.verified_at
    record_audit(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        credential=credential,
        details={"status": "verified", "api_dialect": credential.api_dialect},
        audit_log_service=audit_log_service,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return to_verify_result(credential, result)
