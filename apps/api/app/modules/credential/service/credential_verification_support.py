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
from .dto import CredentialVerifyResultDTO, CredentialVerifyTransportMode
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
    transport_mode: CredentialVerifyTransportMode | None,
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
            transport_mode=transport_mode,
        )
    except Exception as exc:
        await _invalidate_failed_probe_state(
            db,
            credential_id=credential.id,
            failed_probe_kind=probe_kind,
            transport_mode=transport_mode,
        )
        await db.refresh(credential)
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            credential=credential,
            details={
                "status": "failed",
                "error": str(exc),
                "probe_kind": probe_kind,
                "transport_mode": transport_mode,
                **_build_verification_state_snapshot(credential),
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
        transport_mode=result.transport_mode,
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
            "transport_mode": result.transport_mode,
            **_build_verification_state_snapshot(credential),
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
    transport_mode: CredentialVerifyTransportMode | None,
) -> None:
    if transport_mode is None:
        await db.execute(
            update(ModelCredential)
            .where(ModelCredential.id == credential_id)
            .values(
                last_verified_at=verified_at,
                verified_probe_kind=None,
            )
            .execution_options(synchronize_session=False)
        )
        return
    candidate_rank = resolve_conformance_probe_kind_rank(candidate_probe_kind)
    if candidate_rank is None:
        raise ValueError("candidate_probe_kind must be a supported conformance probe kind")
    kind_column, timestamp_column = _resolve_tool_verification_columns(transport_mode)
    await db.execute(
        update(ModelCredential)
        .where(ModelCredential.id == credential_id)
        .values(
            **{
                "verified_probe_kind": None,
                timestamp_column.key: verified_at,
                kind_column.key: _build_promoted_probe_kind_expression(
                    current_probe_kind_column=kind_column,
                    candidate_probe_kind=candidate_probe_kind,
                    candidate_rank=candidate_rank,
                ),
            }
        )
        .execution_options(synchronize_session=False)
    )


async def _invalidate_failed_probe_state(
    db: AsyncSession,
    *,
    credential_id: uuid.UUID,
    failed_probe_kind: ConformanceProbeKind,
    transport_mode: CredentialVerifyTransportMode | None,
) -> None:
    if failed_probe_kind == "text_probe":
        await db.execute(
            update(ModelCredential)
            .where(ModelCredential.id == credential_id)
            .values(
                last_verified_at=None,
                verified_probe_kind=None,
                stream_tool_verified_probe_kind=None,
                stream_tool_last_verified_at=None,
                buffered_tool_verified_probe_kind=None,
                buffered_tool_last_verified_at=None,
            )
            .execution_options(synchronize_session=False)
        )
        return
    if transport_mode is None:
        raise ValueError("tool probe invalidation requires transport_mode")
    failed_rank = resolve_conformance_probe_kind_rank(failed_probe_kind)
    if failed_rank is None:
        raise ValueError("failed_probe_kind must be a supported conformance probe kind")
    kind_column, timestamp_column = _resolve_tool_verification_columns(transport_mode)
    current_rank = _build_current_probe_rank_expression(kind_column)
    await db.execute(
        update(ModelCredential)
        .where(ModelCredential.id == credential_id)
        .values(
            **{
                "verified_probe_kind": None,
                kind_column.key: case(
                    (current_rank >= failed_rank, None),
                    else_=kind_column,
                ),
                timestamp_column.key: case(
                    (current_rank >= failed_rank, None),
                    else_=timestamp_column,
                ),
            }
        )
        .execution_options(synchronize_session=False)
    )


def _build_promoted_probe_kind_expression(
    *,
    current_probe_kind_column,
    candidate_probe_kind: ConformanceProbeKind,
    candidate_rank: int,
):
    current_rank = _build_current_probe_rank_expression(current_probe_kind_column)
    return case(
        (current_rank <= candidate_rank, candidate_probe_kind),
        else_=current_probe_kind_column,
    )


def _build_current_probe_rank_expression(current_probe_kind_column):
    return case(
        *[
            (current_probe_kind_column == probe_kind, rank)
            for probe_kind, rank in CONFORMANCE_PROBE_KIND_RANKS.items()
        ],
        else_=-1,
    )


def _resolve_tool_verification_columns(
    transport_mode: CredentialVerifyTransportMode,
):
    if transport_mode == "buffered":
        return (
            ModelCredential.buffered_tool_verified_probe_kind,
            ModelCredential.buffered_tool_last_verified_at,
        )
    return (
        ModelCredential.stream_tool_verified_probe_kind,
        ModelCredential.stream_tool_last_verified_at,
    )


def _build_verification_state_snapshot(credential: ModelCredential) -> dict[str, object]:
    return {
        "last_verified_at": credential.last_verified_at.isoformat()
        if credential.last_verified_at is not None
        else None,
        "stream_tool_verified_probe_kind": credential.stream_tool_verified_probe_kind,
        "stream_tool_last_verified_at": credential.stream_tool_last_verified_at.isoformat()
        if credential.stream_tool_last_verified_at is not None
        else None,
        "buffered_tool_verified_probe_kind": credential.buffered_tool_verified_probe_kind,
        "buffered_tool_last_verified_at": credential.buffered_tool_last_verified_at.isoformat()
        if credential.buffered_tool_last_verified_at is not None
        else None,
    }
