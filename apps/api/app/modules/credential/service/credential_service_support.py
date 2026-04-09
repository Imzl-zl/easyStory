from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.credential.models import ModelCredential
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import normalize_api_dialect, normalize_custom_base_url

from .credential_connection_support import (
    normalize_api_key_header_name_override,
    normalize_auth_strategy_override,
    normalize_client_identity_settings,
    normalize_connection_settings,
    normalize_extra_headers,
    normalize_interop_profile_override,
    normalize_user_agent_override,
)
from .credential_token_support import (
    normalize_context_window_tokens,
    normalize_default_max_output_tokens,
    update_context_window_tokens,
    update_default_max_output_tokens,
)
from .dto import CredentialUpdateDTO


@dataclass(frozen=True)
class ResolvedCredentialModel:
    credential: ModelCredential
    model_name: str


def apply_update_payload(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    *,
    encrypt_api_key: Callable[[str], str],
) -> dict[str, str]:
    changes: dict[str, str] = {}
    update_api_dialect(credential, payload, changes)
    update_auth_strategy(credential, payload, changes)
    update_api_key_header_name(credential, payload, changes)
    update_extra_headers(credential, payload, changes)
    update_user_agent_override(credential, payload, changes)
    update_client_identity(credential, payload, changes)
    update_display_name(credential, payload, changes)
    update_base_url(credential, payload, changes)
    update_default_model(credential, payload, changes)
    update_interop_profile(credential, payload, changes)
    update_context_window_tokens(credential, payload, changes)
    update_default_max_output_tokens(credential, payload, changes)
    rotate_api_key(credential, payload, encrypt_api_key=encrypt_api_key, changes=changes)
    normalize_connection_settings(credential)
    return changes


def build_credential(
    *,
    owner_type: str,
    owner_id,
    provider: str,
    api_dialect: str,
    display_name: str,
    encrypted_key: str,
    base_url: str | None,
    default_model: str,
    interop_profile: str | None,
    context_window_tokens: int | None,
    default_max_output_tokens: int | None,
    auth_strategy: str | None,
    api_key_header_name: str | None,
    extra_headers: dict[str, str] | None,
    user_agent_override: str | None,
    client_name: str | None,
    client_version: str | None,
    runtime_kind: str | None,
) -> ModelCredential:
    credential = ModelCredential(
        owner_type=owner_type,
        owner_id=owner_id,
        provider=provider,
        api_dialect=normalize_api_dialect(api_dialect),
        display_name=display_name.strip(),
        encrypted_key=encrypted_key,
        base_url=normalize_base_url(base_url),
        default_model=normalize_default_model(default_model),
        interop_profile=interop_profile,
        verified_probe_kind=None,
        stream_tool_verified_probe_kind=None,
        stream_tool_last_verified_at=None,
        buffered_tool_verified_probe_kind=None,
        buffered_tool_last_verified_at=None,
        context_window_tokens=normalize_context_window_tokens(context_window_tokens),
        default_max_output_tokens=normalize_default_max_output_tokens(default_max_output_tokens),
        auth_strategy=auth_strategy,
        api_key_header_name=api_key_header_name,
        extra_headers=extra_headers,
        user_agent_override=user_agent_override,
        client_name=client_name,
        client_version=client_version,
        runtime_kind=runtime_kind,
        is_active=True,
    )
    normalize_connection_settings(credential)
    return credential

def update_api_dialect(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "api_dialect"):
        return
    if payload.api_dialect is None:
        raise ConfigurationError("api_dialect cannot be null")
    api_dialect = normalize_api_dialect(payload.api_dialect)
    if api_dialect == credential.api_dialect:
        return
    credential.api_dialect = api_dialect
    reset_credential_verification_state(credential)
    changes["api_dialect"] = "updated"


def update_auth_strategy(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "auth_strategy"):
        return
    auth_strategy = normalize_auth_strategy_override(credential.api_dialect, payload.auth_strategy)
    if auth_strategy == credential.auth_strategy:
        return
    credential.auth_strategy = auth_strategy
    reset_credential_verification_state(credential)
    changes["auth_strategy"] = "updated"


def update_api_key_header_name(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "api_key_header_name"):
        return
    header_name = normalize_api_key_header_name_override(
        credential.api_dialect,
        credential.auth_strategy,
        payload.api_key_header_name,
    )
    if header_name == credential.api_key_header_name:
        return
    credential.api_key_header_name = header_name
    reset_credential_verification_state(credential)
    changes["api_key_header_name"] = "updated"


def update_extra_headers(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "extra_headers"):
        return
    extra_headers = normalize_extra_headers(
        payload.extra_headers,
        api_dialect=credential.api_dialect,
        auth_strategy=credential.auth_strategy,
        api_key_header_name=credential.api_key_header_name,
    )
    if extra_headers == credential.extra_headers:
        return
    credential.extra_headers = extra_headers
    reset_credential_verification_state(credential)
    changes["extra_headers"] = "updated"


def update_client_identity(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not any(
        (
            _field_was_provided(payload, "client_name"),
            _field_was_provided(payload, "client_version"),
            _field_was_provided(payload, "runtime_kind"),
        )
    ):
        return
    client_name, client_version, runtime_kind = normalize_client_identity_settings(
        client_name=payload.client_name if _field_was_provided(payload, "client_name") else credential.client_name,
        client_version=(
            payload.client_version
            if _field_was_provided(payload, "client_version")
            else credential.client_version
        ),
        runtime_kind=payload.runtime_kind if _field_was_provided(payload, "runtime_kind") else credential.runtime_kind,
    )
    if (
        client_name == credential.client_name
        and client_version == credential.client_version
        and runtime_kind == credential.runtime_kind
    ):
        return
    credential.client_name = client_name
    credential.client_version = client_version
    credential.runtime_kind = runtime_kind
    reset_credential_verification_state(credential)
    changes["client_identity"] = "updated"

def update_user_agent_override(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "user_agent_override"):
        return
    user_agent_override = normalize_user_agent_override(payload.user_agent_override)
    if user_agent_override == credential.user_agent_override:
        return
    credential.user_agent_override = user_agent_override
    reset_credential_verification_state(credential)
    changes["user_agent_override"] = "updated"


def update_display_name(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "display_name"):
        return
    if payload.display_name is None:
        raise ConfigurationError("display_name cannot be null")
    display_name = payload.display_name.strip()
    if display_name == credential.display_name:
        return
    credential.display_name = display_name
    changes["display_name"] = "updated"


def update_base_url(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "base_url"):
        return
    base_url = normalize_base_url(payload.base_url)
    if base_url == credential.base_url:
        return
    credential.base_url = base_url
    reset_credential_verification_state(credential)
    changes["base_url"] = "updated"


def update_default_model(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "default_model"):
        return
    if payload.default_model is None:
        raise ConfigurationError("default_model cannot be null")
    default_model = normalize_default_model(payload.default_model)
    if default_model == credential.default_model:
        return
    credential.default_model = default_model
    reset_credential_verification_state(credential)
    changes["default_model"] = "updated"


def rotate_api_key(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    encrypt_api_key: Callable[[str], str],
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "api_key"):
        return
    if payload.api_key is None:
        raise ConfigurationError("api_key cannot be null")
    credential.encrypted_key = encrypt_api_key(payload.api_key)
    reset_credential_verification_state(credential)
    changes["api_key"] = "rotated"


def update_interop_profile(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if not _field_was_provided(payload, "interop_profile"):
        return
    interop_profile = normalize_interop_profile_override(
        credential.api_dialect,
        payload.interop_profile,
    )
    if interop_profile == credential.interop_profile:
        return
    credential.interop_profile = interop_profile
    reset_credential_verification_state(credential)
    changes["interop_profile"] = "updated"


def reset_credential_verification_state(credential: ModelCredential) -> None:
    credential.last_verified_at = None
    credential.verified_probe_kind = None
    credential.stream_tool_verified_probe_kind = None
    credential.stream_tool_last_verified_at = None
    credential.buffered_tool_verified_probe_kind = None
    credential.buffered_tool_last_verified_at = None


def normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def normalize_default_model(default_model: str | None) -> str | None:
    if default_model is None:
        return None
    normalized = default_model.strip()
    if not normalized:
        raise ConfigurationError("default_model must be a non-empty string")
    return normalized


def normalize_base_url(base_url: str | None) -> str | None:
    return normalize_custom_base_url(base_url)


def _field_was_provided(payload: CredentialUpdateDTO, field_name: str) -> bool:
    return field_name in payload.model_fields_set
