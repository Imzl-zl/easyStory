from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.infrastructure import (
    AsyncCredentialVerifier,
    CredentialCipher,
)
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AuditLogService
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import NotFoundError
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
)

from .dto import (
    CredentialCreateDTO,
    CredentialVerifyTransportMode,
    CredentialUpdateDTO,
    CredentialVerifyResultDTO,
    CredentialViewDTO,
)
from .credential_query_support import (
    ensure_credential_is_deletable,
    ensure_unique_provider,
    require_actor_credential,
    resolve_actor_scope,
    scope_statement,
)
from .credential_mutation_support import record_audit, set_active_state
from .credential_resolution_support import (
    resolve_active_credential_model_record,
    resolve_active_credential_record,
)
from .credential_service_support import (
    ResolvedCredentialModel,
    apply_update_payload,
    build_credential,
    normalize_provider,
)
from .credential_view_support import to_view
from .credential_verification_support import verify_credential_record

AUDIT_CREATE = "credential_create"
AUDIT_UPDATE = "credential_update"
AUDIT_DELETE = "credential_delete"
AUDIT_VERIFY = "credential_verify"
AUDIT_ENABLE = "credential_enable"
AUDIT_DISABLE = "credential_disable"


class CredentialService:
    def __init__(
        self,
        crypto: CredentialCipher,
        verifier: AsyncCredentialVerifier,
        audit_log_service: AuditLogService,
        project_service: ProjectService,
    ) -> None:
        self.crypto = crypto
        self.verifier = verifier
        self.audit_log_service = audit_log_service
        self.project_service = project_service

    async def list_credentials(
        self,
        db: AsyncSession,
        *,
        actor_user_id: uuid.UUID,
        owner_type: str,
        project_id: uuid.UUID | None = None,
    ) -> list[CredentialViewDTO]:
        scope = await resolve_actor_scope(
            db,
            actor_user_id=actor_user_id,
            owner_type=owner_type,
            project_id=project_id,
            project_service=self.project_service,
        )
        statement = scope_statement(scope).order_by(
            ModelCredential.updated_at.desc(),
            ModelCredential.created_at.desc(),
        )
        credentials = (await db.scalars(statement)).all()
        return [to_view(item, decrypt_api_key=self.crypto.decrypt) for item in credentials]

    async def create_credential(
        self,
        db: AsyncSession,
        payload: CredentialCreateDTO,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        scope = await resolve_actor_scope(
            db,
            actor_user_id=actor_user_id,
            owner_type=payload.owner_type,
            project_id=payload.project_id,
            project_service=self.project_service,
        )
        provider = normalize_provider(payload.provider)
        await ensure_unique_provider(db, scope=scope, provider=provider)
        credential = build_credential(
            owner_type=scope.owner_type,
            owner_id=scope.owner_id,
            provider=provider,
            api_dialect=payload.api_dialect,
            display_name=payload.display_name,
            encrypted_key=self.crypto.encrypt(payload.api_key),
            base_url=payload.base_url,
            default_model=payload.default_model,
            interop_profile=payload.interop_profile,
            context_window_tokens=payload.context_window_tokens,
            default_max_output_tokens=payload.default_max_output_tokens,
            auth_strategy=payload.auth_strategy,
            api_key_header_name=payload.api_key_header_name,
            extra_headers=payload.extra_headers,
            user_agent_override=payload.user_agent_override,
            client_name=payload.client_name,
            client_version=payload.client_version,
            runtime_kind=payload.runtime_kind,
        )
        db.add(credential)
        await db.flush()
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_CREATE,
            credential=credential,
            details={"provider": credential.provider},
            audit_log_service=self.audit_log_service,
        )
        await db.commit()
        await db.refresh(credential)
        return to_view(credential, decrypt_api_key=self.crypto.decrypt)

    async def update_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        payload: CredentialUpdateDTO,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        credential = await require_actor_credential(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            project_service=self.project_service,
        )
        changes = apply_update_payload(
            credential,
            payload,
            encrypt_api_key=self.crypto.encrypt,
        )
        if not changes:
            return to_view(credential, decrypt_api_key=self.crypto.decrypt)
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_UPDATE,
            credential=credential,
            details=changes,
            audit_log_service=self.audit_log_service,
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return to_view(credential, decrypt_api_key=self.crypto.decrypt)

    async def delete_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> None:
        credential = await require_actor_credential(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            project_service=self.project_service,
        )
        await ensure_credential_is_deletable(db, credential.id)
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_DELETE,
            credential=credential,
            details={"provider": credential.provider},
            audit_log_service=self.audit_log_service,
        )
        await db.delete(credential)
        await db.commit()

    async def enable_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        return await set_active_state(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            is_active=True,
            event_type=AUDIT_ENABLE,
            project_service=self.project_service,
            audit_log_service=self.audit_log_service,
            decrypt_api_key=self.crypto.decrypt,
        )

    async def disable_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        return await set_active_state(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            is_active=False,
            event_type=AUDIT_DISABLE,
            project_service=self.project_service,
            audit_log_service=self.audit_log_service,
            decrypt_api_key=self.crypto.decrypt,
        )

    async def verify_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        probe_kind: ConformanceProbeKind = "text_probe",
        transport_mode: CredentialVerifyTransportMode | None = None,
    ) -> CredentialVerifyResultDTO:
        credential = await require_actor_credential(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            project_service=self.project_service,
        )
        return await verify_credential_record(
            db,
            credential=credential,
            verifier=self.verifier,
            decrypt_api_key=self.crypto.decrypt,
            actor_user_id=actor_user_id,
            event_type=AUDIT_VERIFY,
            audit_log_service=self.audit_log_service,
            probe_kind=probe_kind,
            transport_mode=transport_mode,
        )

    async def resolve_active_credential(
        self,
        db: AsyncSession,
        *,
        provider: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ModelCredential:
        try:
            return await resolve_active_credential_record(
                db,
                provider=provider,
                user_id=user_id,
                project_id=project_id,
                project_service=self.project_service,
            )
        except LookupError as exc:
            raise NotFoundError(f"Credential not found for provider: {exc.args[0]}") from exc

    async def resolve_active_credential_model(
        self,
        db: AsyncSession,
        *,
        provider: str,
        requested_model_name: str | None,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ResolvedCredentialModel:
        try:
            return await resolve_active_credential_model_record(
                db,
                provider=provider,
                requested_model_name=requested_model_name,
                user_id=user_id,
                project_id=project_id,
                project_service=self.project_service,
            )
        except LookupError as exc:
            raise NotFoundError(f"Credential not found for provider: {exc.args[0]}") from exc
