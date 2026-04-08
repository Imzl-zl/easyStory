from __future__ import annotations

import uuid

from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.infrastructure import AsyncCredentialVerifier
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AuditLogService
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    CONFORMANCE_PROBE_KIND_RANKS,
    ConformanceProbeKind,
    resolve_conformance_probe_kind_rank,
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
    await _persist_verified_probe_state(
        db,
        credential_id=credential.id,
        verified_at=result.verified_at,
        candidate_probe_kind=result.probe_kind,
    )
    await db.refresh(credential)
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
    await db.commit()
    return to_verify_result(credential, result)


async def _persist_verified_probe_state(
    db: AsyncSession,
    *,
    credential_id: uuid.UUID,
    verified_at,
    candidate_probe_kind: ConformanceProbeKind,
) -> None:
    candidate_rank = resolve_conformance_probe_kind_rank(candidate_probe_kind)
    if candidate_rank is None:
        raise ValueError("candidate_probe_kind must be a supported conformance probe kind")
    await db.execute(
        update(ModelCredential)
        .where(ModelCredential.id == credential_id)
        .values(
            last_verified_at=verified_at,
            verified_probe_kind=_build_promoted_probe_kind_expression(
                candidate_probe_kind=candidate_probe_kind,
                candidate_rank=candidate_rank,
            ),
        )
        .execution_options(synchronize_session=False)
    )


def _build_promoted_probe_kind_expression(
    *,
    candidate_probe_kind: ConformanceProbeKind,
    candidate_rank: int,
):
    current_rank = case(
        *[
            (ModelCredential.verified_probe_kind == probe_kind, rank)
            for probe_kind, rank in CONFORMANCE_PROBE_KIND_RANKS.items()
        ],
        else_=-1,
    )
    return case(
        (current_rank <= candidate_rank, candidate_probe_kind),
        else_=ModelCredential.verified_probe_kind,
    )
