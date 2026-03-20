from __future__ import annotations

from app.modules.credential.infrastructure import CredentialCrypto, HttpCredentialVerifier
from app.modules.observability.service import AuditLogService, create_audit_log_service
from app.modules.project.service import ProjectService, create_project_service

from .credential_service import CredentialService


def create_credential_service(
    *,
    crypto: CredentialCrypto | None = None,
    verifier: HttpCredentialVerifier | None = None,
    audit_log_service: AuditLogService | None = None,
    project_service: ProjectService | None = None,
) -> CredentialService:
    return CredentialService(
        crypto=crypto or CredentialCrypto(),
        verifier=verifier or HttpCredentialVerifier(),
        audit_log_service=audit_log_service or create_audit_log_service(),
        project_service=project_service or create_project_service(),
    )
