from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.infrastructure import (
    AsyncCredentialVerifier,
    CredentialCrypto,
)
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import AuditLogService
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import NotFoundError

from .dto import (
    CredentialCreateDTO,
    CredentialUpdateDTO,
    CredentialVerifyResultDTO,
    CredentialViewDTO,
)
from .credential_query_support import (
    OWNER_TYPE_PROJECT,
    OWNER_TYPE_SYSTEM,
    OWNER_TYPE_USER,
    ensure_credential_is_deletable,
    ensure_unique_provider,
    find_active_credential,
    load_project_if_present,
    require_actor_credential,
    resolve_actor_scope,
    scope_statement,
)
from .credential_mutation_support import record_audit, set_active_state
from .credential_service_support import apply_update_payload, normalize_base_url, normalize_provider, to_verify_result, to_view

AUDIT_CREATE = "credential_create"
AUDIT_UPDATE = "credential_update"
AUDIT_DELETE = "credential_delete"
AUDIT_VERIFY = "credential_verify"
AUDIT_ENABLE = "credential_enable"
AUDIT_DISABLE = "credential_disable"


class CredentialService:
    def __init__(
        self,
        crypto: CredentialCrypto,
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
        statement = scope_statement(scope).order_by(ModelCredential.created_at.desc())
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
        credential = ModelCredential(
            owner_type=scope.owner_type,
            owner_id=scope.owner_id,
            provider=provider,
            display_name=payload.display_name.strip(),
            encrypted_key=self.crypto.encrypt(payload.api_key),
            base_url=normalize_base_url(payload.base_url),
            is_active=True,
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
    ) -> CredentialVerifyResultDTO:
        credential = await require_actor_credential(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            project_service=self.project_service,
        )
        api_key = self.crypto.decrypt(credential.encrypted_key)
        try:
            result = await self.verifier.verify(
                provider=credential.provider,
                api_key=api_key,
                base_url=credential.base_url,
            )
        except Exception as exc:
            record_audit(
                db,
                actor_user_id=actor_user_id,
                event_type=AUDIT_VERIFY,
                credential=credential,
                details={"status": "failed", "error": str(exc)},
                audit_log_service=self.audit_log_service,
            )
            await db.commit()
            raise
        credential.last_verified_at = result.verified_at
        record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_VERIFY,
            credential=credential,
            details={"status": "verified"},
            audit_log_service=self.audit_log_service,
        )
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return to_verify_result(credential, result)

    async def resolve_active_credential(
        self,
        db: AsyncSession,
        *,
        provider: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ModelCredential:
        normalized_provider = normalize_provider(provider)
        project = await load_project_if_present(
            db,
            project_id,
            owner_id=user_id,
            project_service=self.project_service,
        )
        if project is not None:
            project_credential = await find_active_credential(
                db,
                owner_type=OWNER_TYPE_PROJECT,
                owner_id=project.id,
                provider=normalized_provider,
            )
            if project_credential is not None:
                return project_credential
        user_credential = await find_active_credential(
            db,
            owner_type=OWNER_TYPE_USER,
            owner_id=user_id,
            provider=normalized_provider,
        )
        if user_credential is not None:
            return user_credential
        if project is not None and project.allow_system_credential_pool:
            system_credential = await find_active_credential(
                db,
                owner_type=OWNER_TYPE_SYSTEM,
                owner_id=None,
                provider=normalized_provider,
            )
            if system_credential is not None:
                return system_credential
        raise NotFoundError(f"Credential not found for provider: {normalized_provider}")
