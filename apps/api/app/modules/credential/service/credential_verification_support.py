from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.infrastructure import AsyncCredentialVerifier
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AuditLogService
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
    promote_conformance_probe_kind,
)

from .credential_mutation_support import record_audit
from .dto import CredentialVerifyResultDTO
from .credential_view_support import to_verify_result


async def verify_credential_record(
    db: AsyncSession,
    *,
    credential: ModelCredential,
    verifier: AsyncCredentialVerifier,
    decrypt_api_key,
    actor_user_id: uuid.UUID,
    event_type: str,
    audit_log_service: AuditLogService,
    probe_kind: ConformanceProbeKind,
) -> CredentialVerifyResultDTO:
    api_key = decrypt_api_key(credential.encrypted_key)
    try:
        result = await verifier.verify(
            provider=credential.provider,
            api_key=api_key,
            base_url=credential.base_url,
            api_dialect=credential.api_dialect,
            default_model=credential.default_model,
            interop_profile=credential.interop_profile,
            auth_strategy=credential.auth_strategy,
            api_key_header_name=credential.api_key_header_name,
            extra_headers=credential.extra_headers,
            user_agent_override=credential.user_agent_override,
            client_name=credential.client_name,
            client_version=credential.client_version,
            runtime_kind=credential.runtime_kind,
            probe_kind=probe_kind,
        )
    except Exception as exc:
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            credential=credential,
            details={
                "status": "failed",
                "error": str(exc),
                "probe_kind": probe_kind,
            },
            audit_log_service=audit_log_service,
        )
        await db.commit()
        raise
    credential.last_verified_at = result.verified_at
    credential.verified_probe_kind = promote_conformance_probe_kind(
        credential.verified_probe_kind,
        result.probe_kind,
    )
    record_audit(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        credential=credential,
        details={
            "status": "verified",
            "api_dialect": credential.api_dialect,
            "probe_kind": probe_kind,
            "verified_probe_kind": credential.verified_probe_kind,
        },
        audit_log_service=audit_log_service,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return to_verify_result(credential, result)
