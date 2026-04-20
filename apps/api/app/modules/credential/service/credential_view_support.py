from __future__ import annotations

from collections.abc import Callable

from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.models import ModelCredential
from app.shared.runtime.llm.llm_protocol_types import normalize_api_dialect

from .credential_connection_support import copy_extra_headers
from .dto import CredentialVerifyResultDTO, CredentialViewDTO

MASKED_KEY_MIN_LENGTH = 7
MASKED_VISIBLE_PREFIX = 3
MASKED_VISIBLE_SUFFIX = 4


def to_view(
    credential: ModelCredential,
    *,
    decrypt_api_key: Callable[[str], str],
) -> CredentialViewDTO:
    return CredentialViewDTO(
        id=credential.id,
        owner_type=credential.owner_type,
        owner_id=credential.owner_id,
        provider=credential.provider,
        api_dialect=normalize_api_dialect(credential.api_dialect),
        display_name=credential.display_name,
        masked_key=mask_key(decrypt_api_key(credential.encrypted_key)),
        base_url=credential.base_url,
        default_model=credential.default_model,
        interop_profile=credential.interop_profile,
        stream_tool_verified_probe_kind=credential.stream_tool_verified_probe_kind,
        stream_tool_last_verified_at=credential.stream_tool_last_verified_at,
        buffered_tool_verified_probe_kind=credential.buffered_tool_verified_probe_kind,
        buffered_tool_last_verified_at=credential.buffered_tool_last_verified_at,
        context_window_tokens=credential.context_window_tokens,
        default_max_output_tokens=credential.default_max_output_tokens,
        auth_strategy=credential.auth_strategy,
        api_key_header_name=credential.api_key_header_name,
        extra_headers=copy_extra_headers(credential.extra_headers),
        user_agent_override=credential.user_agent_override,
        client_name=credential.client_name,
        client_version=credential.client_version,
        runtime_kind=credential.runtime_kind,
        is_active=credential.is_active,
        last_verified_at=credential.last_verified_at,
    )


def to_verify_result(
    credential: ModelCredential,
    result: CredentialVerificationResult,
) -> CredentialVerifyResultDTO:
    return CredentialVerifyResultDTO(
        credential_id=credential.id,
        probe_kind=result.probe_kind,
        transport_mode=result.transport_mode,
        last_verified_at=result.verified_at,
        message=result.message,
    )


def mask_key(api_key: str) -> str:
    if len(api_key) < MASKED_KEY_MIN_LENGTH:
        return "***"
    return f"{api_key[:MASKED_VISIBLE_PREFIX]}...{api_key[-MASKED_VISIBLE_SUFFIX:]}"
