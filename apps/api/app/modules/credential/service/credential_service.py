from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.credential.infrastructure import (
    CredentialCrypto,
    CredentialVerificationResult,
    CredentialVerifier,
)
from app.modules.credential.models import ModelCredential
from app.modules.observability.service import (
    AUDIT_ENTITY_MODEL_CREDENTIAL,
    AuditLogService,
)
from app.modules.project.models import Project
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError

from .dto import (
    CredentialCreateDTO,
    CredentialUpdateDTO,
    CredentialVerifyResultDTO,
    CredentialViewDTO,
)

OWNER_TYPE_SYSTEM = "system"
OWNER_TYPE_USER = "user"
OWNER_TYPE_PROJECT = "project"
AUDIT_CREATE = "credential_create"
AUDIT_UPDATE = "credential_update"
AUDIT_DELETE = "credential_delete"
AUDIT_VERIFY = "credential_verify"
AUDIT_ENABLE = "credential_enable"
AUDIT_DISABLE = "credential_disable"
MASKED_KEY_MIN_LENGTH = 7
MASKED_VISIBLE_PREFIX = 3
MASKED_VISIBLE_SUFFIX = 4


@dataclass(frozen=True)
class CredentialScope:
    owner_type: str
    owner_id: uuid.UUID | None


class CredentialService:
    def __init__(
        self,
        crypto: CredentialCrypto,
        verifier: CredentialVerifier,
        audit_log_service: AuditLogService,
        project_service: ProjectService,
    ) -> None:
        self.crypto = crypto
        self.verifier = verifier
        self.audit_log_service = audit_log_service
        self.project_service = project_service

    def list_credentials(
        self,
        db: Session,
        *,
        actor_user_id: uuid.UUID,
        owner_type: str,
        project_id: uuid.UUID | None = None,
    ) -> list[CredentialViewDTO]:
        scope = self._resolve_actor_scope(
            db,
            actor_user_id=actor_user_id,
            owner_type=owner_type,
            project_id=project_id,
        )
        credentials = (
            self._query_scope(db, scope)
            .order_by(ModelCredential.created_at.desc())
            .all()
        )
        return [self._to_view(item) for item in credentials]

    def create_credential(
        self,
        db: Session,
        payload: CredentialCreateDTO,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        scope = self._resolve_actor_scope(
            db,
            actor_user_id=actor_user_id,
            owner_type=payload.owner_type,
            project_id=payload.project_id,
        )
        provider = _normalize_provider(payload.provider)
        self._ensure_unique_provider(db, scope, provider)
        credential = ModelCredential(
            owner_type=scope.owner_type,
            owner_id=scope.owner_id,
            provider=provider,
            display_name=payload.display_name.strip(),
            encrypted_key=self.crypto.encrypt(payload.api_key),
            base_url=_normalize_base_url(payload.base_url),
            is_active=True,
        )
        db.add(credential)
        db.flush()
        self._record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_CREATE,
            credential=credential,
            details={"provider": credential.provider},
        )
        db.commit()
        db.refresh(credential)
        return self._to_view(credential)

    def update_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        payload: CredentialUpdateDTO,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        credential = self._require_actor_credential(db, credential_id, actor_user_id=actor_user_id)
        changes = self._apply_update_payload(credential, payload)
        if not changes:
            return self._to_view(credential)
        self._record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_UPDATE,
            credential=credential,
            details=changes,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return self._to_view(credential)

    def delete_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> None:
        credential = self._require_actor_credential(db, credential_id, actor_user_id=actor_user_id)
        self._record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_DELETE,
            credential=credential,
            details={"provider": credential.provider},
        )
        db.delete(credential)
        db.commit()

    def enable_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        return self._set_active_state(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            is_active=True,
        )

    def disable_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialViewDTO:
        return self._set_active_state(
            db,
            credential_id,
            actor_user_id=actor_user_id,
            is_active=False,
        )

    def verify_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> CredentialVerifyResultDTO:
        credential = self._require_actor_credential(db, credential_id, actor_user_id=actor_user_id)
        api_key = self.crypto.decrypt(credential.encrypted_key)
        try:
            result = self.verifier.verify(
                provider=credential.provider,
                api_key=api_key,
                base_url=credential.base_url,
            )
        except Exception as exc:
            self._record_audit(
                db,
                actor_user_id=actor_user_id,
                event_type=AUDIT_VERIFY,
                credential=credential,
                details={"status": "failed", "error": str(exc)},
            )
            db.commit()
            raise
        credential.last_verified_at = result.verified_at
        self._record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=AUDIT_VERIFY,
            credential=credential,
            details={"status": "verified"},
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return self._to_verify_result(credential, result)

    def resolve_active_credential(
        self,
        db: Session,
        *,
        provider: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ModelCredential:
        normalized_provider = _normalize_provider(provider)
        project = self._load_project_if_present(db, project_id, owner_id=user_id)
        if project is not None:
            project_credential = self._find_active_credential(
                db,
                owner_type=OWNER_TYPE_PROJECT,
                owner_id=project.id,
                provider=normalized_provider,
            )
            if project_credential is not None:
                return project_credential
        user_credential = self._find_active_credential(
            db,
            owner_type=OWNER_TYPE_USER,
            owner_id=user_id,
            provider=normalized_provider,
        )
        if user_credential is not None:
            return user_credential
        if project is not None and project.allow_system_credential_pool:
            system_credential = self._find_active_credential(
                db,
                owner_type=OWNER_TYPE_SYSTEM,
                owner_id=None,
                provider=normalized_provider,
            )
            if system_credential is not None:
                return system_credential
        raise NotFoundError(f"Credential not found for provider: {normalized_provider}")

    def _resolve_actor_scope(
        self,
        db: Session,
        *,
        actor_user_id: uuid.UUID,
        owner_type: str,
        project_id: uuid.UUID | None,
    ) -> CredentialScope:
        if owner_type == OWNER_TYPE_USER:
            if project_id is not None:
                raise BusinessRuleError("user scope does not accept project_id")
            return CredentialScope(owner_type=OWNER_TYPE_USER, owner_id=actor_user_id)
        if owner_type == OWNER_TYPE_PROJECT:
            if project_id is None:
                raise BusinessRuleError("project scope requires project_id")
            project = self.project_service.require_project(
                db,
                project_id,
                owner_id=actor_user_id,
            )
            return CredentialScope(owner_type=OWNER_TYPE_PROJECT, owner_id=project.id)
        raise BusinessRuleError("system scope is not available via user API")

    def _require_actor_credential(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> ModelCredential:
        credential = (
            db.query(ModelCredential)
            .filter(ModelCredential.id == credential_id)
            .one_or_none()
        )
        if credential is None:
            raise NotFoundError(f"Credential not found: {credential_id}")
        if credential.owner_type == OWNER_TYPE_USER:
            if credential.owner_id != actor_user_id:
                raise NotFoundError(f"Credential not found: {credential_id}")
            return credential
        if credential.owner_type == OWNER_TYPE_PROJECT:
            self.project_service.require_project(
                db,
                credential.owner_id,
                owner_id=actor_user_id,
            )
            return credential
        raise NotFoundError(f"Credential not found: {credential_id}")

    def _query_scope(self, db: Session, scope: CredentialScope):
        query = db.query(ModelCredential).filter(ModelCredential.owner_type == scope.owner_type)
        if scope.owner_id is None:
            return query.filter(ModelCredential.owner_id.is_(None))
        return query.filter(ModelCredential.owner_id == scope.owner_id)

    def _ensure_unique_provider(
        self,
        db: Session,
        scope: CredentialScope,
        provider: str,
    ) -> None:
        exists = (
            self._query_scope(db, scope)
            .filter(ModelCredential.provider == provider)
            .one_or_none()
        )
        if exists is not None:
            raise ConflictError(
                f"Credential already exists for provider '{provider}' in scope '{scope.owner_type}'"
            )

    def _apply_update_payload(
        self,
        credential: ModelCredential,
        payload: CredentialUpdateDTO,
    ) -> dict[str, str]:
        changes: dict[str, str] = {}
        if payload.display_name is not None and payload.display_name.strip() != credential.display_name:
            credential.display_name = payload.display_name.strip()
            changes["display_name"] = "updated"
        normalized_base_url = _normalize_base_url(payload.base_url)
        if payload.base_url is not None and normalized_base_url != credential.base_url:
            credential.base_url = normalized_base_url
            credential.last_verified_at = None
            changes["base_url"] = "updated"
        if payload.api_key is not None:
            credential.encrypted_key = self.crypto.encrypt(payload.api_key)
            credential.last_verified_at = None
            changes["api_key"] = "rotated"
        return changes

    def _set_active_state(
        self,
        db: Session,
        credential_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        is_active: bool,
    ) -> CredentialViewDTO:
        credential = self._require_actor_credential(db, credential_id, actor_user_id=actor_user_id)
        if credential.is_active == is_active:
            return self._to_view(credential)
        credential.is_active = is_active
        event_type = AUDIT_ENABLE if is_active else AUDIT_DISABLE
        self._record_audit(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            credential=credential,
            details=None,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return self._to_view(credential)

    def _load_project_if_present(
        self,
        db: Session,
        project_id: uuid.UUID | None,
        *,
        owner_id: uuid.UUID,
    ) -> Project | None:
        if project_id is None:
            return None
        return self.project_service.require_project(db, project_id, owner_id=owner_id)

    def _find_active_credential(
        self,
        db: Session,
        *,
        owner_type: str,
        owner_id: uuid.UUID | None,
        provider: str,
    ) -> ModelCredential | None:
        query = (
            db.query(ModelCredential)
            .filter(
                ModelCredential.owner_type == owner_type,
                ModelCredential.provider == provider,
                ModelCredential.is_active.is_(True),
            )
            .order_by(ModelCredential.updated_at.desc(), ModelCredential.created_at.desc())
        )
        if owner_id is None:
            return query.filter(ModelCredential.owner_id.is_(None)).one_or_none()
        return query.filter(ModelCredential.owner_id == owner_id).one_or_none()

    def _record_audit(
        self,
        db: Session,
        *,
        actor_user_id: uuid.UUID | None,
        event_type: str,
        credential: ModelCredential,
        details: dict | None,
    ) -> None:
        payload = {
            "provider": credential.provider,
            "owner_type": credential.owner_type,
            "owner_id": str(credential.owner_id) if credential.owner_id is not None else None,
        }
        if details:
            payload.update(details)
        self.audit_log_service.record(
            db,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=AUDIT_ENTITY_MODEL_CREDENTIAL,
            entity_id=credential.id,
            details=payload,
        )

    def _to_view(self, credential: ModelCredential) -> CredentialViewDTO:
        return CredentialViewDTO(
            id=credential.id,
            owner_type=credential.owner_type,
            owner_id=credential.owner_id,
            provider=credential.provider,
            display_name=credential.display_name,
            masked_key=_mask_key(self.crypto.decrypt(credential.encrypted_key)),
            base_url=credential.base_url,
            is_active=credential.is_active,
            last_verified_at=credential.last_verified_at,
        )

    def _to_verify_result(
        self,
        credential: ModelCredential,
        result: CredentialVerificationResult,
    ) -> CredentialVerifyResultDTO:
        return CredentialVerifyResultDTO(
            credential_id=credential.id,
            last_verified_at=result.verified_at,
            message=result.message,
        )


def _normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def _normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip()
    return normalized or None


def _mask_key(api_key: str) -> str:
    if len(api_key) < MASKED_KEY_MIN_LENGTH:
        return "***"
    return (
        f"{api_key[:MASKED_VISIBLE_PREFIX]}..."
        f"{api_key[-MASKED_VISIBLE_SUFFIX:]}"
    )
