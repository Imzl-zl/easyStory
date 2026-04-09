from __future__ import annotations

from app.modules.credential.infrastructure import (
    AsyncCredentialVerifier,
    AsyncHttpCredentialVerifier,
    CredentialCipher,
    CredentialCrypto,
    CredentialVerificationResult,
)
from app.modules.observability.service import AuditLogService, create_audit_log_service
from app.modules.project.service import ProjectService, create_project_service

from .credential_service import CredentialService


class _UnsupportedCredentialCrypto:
    def encrypt(self, _value: str) -> str:
        raise RuntimeError("Credential resolution service does not support encryption")

    def decrypt(self, _value: str) -> str:
        raise RuntimeError("Credential resolution service does not support decryption")


class _UnsupportedCredentialVerifier:
    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        interop_profile: str | None = None,
        auth_strategy: str | None = None,
        api_key_header_name: str | None = None,
        extra_headers: dict[str, str] | None = None,
        user_agent_override: str | None = None,
        client_name: str | None = None,
        client_version: str | None = None,
        runtime_kind: str | None = None,
        probe_kind: str | None = None,
        transport_mode: str | None = None,
    ) -> CredentialVerificationResult:
        del (
            provider,
            api_key,
            base_url,
            api_dialect,
            default_model,
            interop_profile,
            auth_strategy,
            api_key_header_name,
            extra_headers,
            user_agent_override,
            client_name,
            client_version,
            runtime_kind,
            probe_kind,
            transport_mode,
        )
        raise RuntimeError("Credential resolution service does not support verification")


def create_credential_service(
    *,
    crypto: CredentialCipher | None = None,
    verifier: AsyncCredentialVerifier | None = None,
    audit_log_service: AuditLogService | None = None,
    project_service: ProjectService | None = None,
) -> CredentialService:
    return CredentialService(
        crypto=crypto or CredentialCrypto(),
        verifier=verifier or AsyncHttpCredentialVerifier(),
        audit_log_service=audit_log_service or create_audit_log_service(),
        project_service=project_service or create_project_service(),
    )


def create_credential_resolution_service(
    *,
    project_service: ProjectService | None = None,
) -> CredentialService:
    return CredentialService(
        crypto=_UnsupportedCredentialCrypto(),
        verifier=_UnsupportedCredentialVerifier(),
        audit_log_service=create_audit_log_service(),
        project_service=project_service or create_project_service(),
    )
