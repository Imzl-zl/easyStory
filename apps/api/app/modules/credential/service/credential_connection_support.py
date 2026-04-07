from __future__ import annotations

from collections.abc import Callable

from app.modules.credential.models import ModelCredential
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import (
    normalize_api_dialect,
    normalize_auth_strategy,
    normalize_http_header_name,
    normalize_runtime_kind,
    resolve_api_key_header_name,
    resolve_auth_strategy,
)

CONTENT_TYPE_HEADER_NAME = "content-type"
ANTHROPIC_VERSION_HEADER_NAME = "anthropic-version"
USER_AGENT_HEADER_NAME = "user-agent"
SENSITIVE_EXTRA_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-goog-api-key",
    }
)
SENSITIVE_EXTRA_HEADER_FRAGMENTS = ("token", "secret", "api-key", "api_key")


def normalize_connection_settings(credential: ModelCredential) -> None:
    credential.auth_strategy = normalize_auth_strategy_override(
        credential.api_dialect,
        credential.auth_strategy,
    )
    credential.api_key_header_name = normalize_api_key_header_name_override(
        credential.api_dialect,
        credential.auth_strategy,
        credential.api_key_header_name,
    )
    credential.extra_headers = normalize_extra_headers(
        credential.extra_headers,
        api_dialect=credential.api_dialect,
        auth_strategy=credential.auth_strategy,
        api_key_header_name=credential.api_key_header_name,
    )
    credential.user_agent_override = normalize_user_agent_override(credential.user_agent_override)
    credential.client_name, credential.client_version, credential.runtime_kind = normalize_client_identity_settings(
        client_name=credential.client_name,
        client_version=credential.client_version,
        runtime_kind=credential.runtime_kind,
    )


def build_runtime_credential_payload(
    credential: ModelCredential,
    *,
    decrypt_api_key: Callable[[str], str],
) -> dict[str, object]:
    return {
        "api_key": decrypt_api_key(credential.encrypted_key),
        "api_dialect": credential.api_dialect,
        "base_url": credential.base_url,
        "default_model": credential.default_model,
        "context_window_tokens": credential.context_window_tokens,
        "default_max_output_tokens": credential.default_max_output_tokens,
        "auth_strategy": credential.auth_strategy,
        "api_key_header_name": credential.api_key_header_name,
        "extra_headers": copy_extra_headers(credential.extra_headers),
        "user_agent_override": credential.user_agent_override,
        "client_name": credential.client_name,
        "client_version": credential.client_version,
        "runtime_kind": credential.runtime_kind,
    }


def normalize_client_identity_settings(
    *,
    client_name: str | None,
    client_version: str | None,
    runtime_kind: str | None,
) -> tuple[str | None, str | None, str | None]:
    normalized_name = _normalize_optional_string(client_name)
    normalized_version = _normalize_optional_string(client_version)
    normalized_runtime_kind = normalize_runtime_kind(runtime_kind)
    if normalized_name is None and (normalized_version is not None or normalized_runtime_kind is not None):
        raise ConfigurationError("client_name is required when client_version or runtime_kind is provided")
    if normalized_name is None:
        return None, None, None
    return normalized_name, normalized_version, normalized_runtime_kind


def normalize_user_agent_override(user_agent_override: str | None) -> str | None:
    normalized = _normalize_optional_string(user_agent_override)
    if normalized is None:
        return None
    if "\r" in normalized or "\n" in normalized:
        raise ConfigurationError("user_agent_override must be a single-line header value")
    return normalized


def normalize_auth_strategy_override(
    api_dialect: str,
    auth_strategy: str | None,
) -> str | None:
    explicit_strategy = normalize_auth_strategy(auth_strategy)
    if explicit_strategy is None:
        return None
    if explicit_strategy == resolve_auth_strategy(api_dialect, None):
        return None
    return explicit_strategy


def normalize_api_key_header_name_override(
    api_dialect: str,
    auth_strategy: str | None,
    api_key_header_name: str | None,
) -> str | None:
    normalized_header_name = normalize_http_header_name(api_key_header_name)
    strategy = resolve_auth_strategy(api_dialect, auth_strategy)
    resolve_api_key_header_name(
        api_dialect=api_dialect,
        auth_strategy=auth_strategy,
        api_key_header_name=normalized_header_name,
    )
    if strategy != "custom_header":
        return None
    _ensure_custom_auth_header_name_is_allowed(normalized_header_name, api_dialect=api_dialect)
    return normalized_header_name


def normalize_extra_headers(
    extra_headers: dict[str, str] | None,
    *,
    api_dialect: str,
    auth_strategy: str | None,
    api_key_header_name: str | None,
) -> dict[str, str] | None:
    if extra_headers is None:
        return None
    normalized: dict[str, str] = {}
    for raw_name, raw_value in extra_headers.items():
        if not isinstance(raw_name, str):
            raise ConfigurationError("extra_headers keys must be strings")
        if not isinstance(raw_value, str):
            raise ConfigurationError("extra_headers values must be strings")
        header_name = normalize_http_header_name(raw_name)
        if header_name is None:
            raise ConfigurationError("extra_headers keys must be valid HTTP header names")
        header_value = raw_value.strip()
        if not header_value:
            raise ConfigurationError("extra_headers values must be non-empty strings")
        normalized[header_name] = header_value
    _ensure_headers_do_not_override_runtime_controls(
        normalized,
        api_dialect=api_dialect,
        auth_strategy=auth_strategy,
        api_key_header_name=api_key_header_name,
    )
    _ensure_headers_are_non_sensitive(normalized)
    return normalized or None


def copy_extra_headers(extra_headers: dict[str, str] | None) -> dict[str, str] | None:
    if extra_headers is None:
        return None
    return dict(extra_headers)


def _ensure_headers_do_not_override_runtime_controls(
    extra_headers: dict[str, str],
    *,
    api_dialect: str,
    auth_strategy: str | None,
    api_key_header_name: str | None,
) -> None:
    reserved_headers = _build_runtime_reserved_headers(
        api_dialect=api_dialect,
        auth_strategy=auth_strategy,
        api_key_header_name=api_key_header_name,
    )
    conflicting_headers = [
        header_name for header_name in extra_headers if header_name.lower() in reserved_headers
    ]
    if conflicting_headers:
        headers_text = ", ".join(sorted(conflicting_headers, key=str.lower))
        raise ConfigurationError(f"extra_headers cannot override runtime-managed headers: {headers_text}")


def _ensure_custom_auth_header_name_is_allowed(
    header_name: str | None,
    *,
    api_dialect: str,
) -> None:
    if header_name is None:
        return
    reserved_headers = _build_runtime_reserved_headers(
        api_dialect=api_dialect,
        auth_strategy=None,
        api_key_header_name=None,
        include_auth_header=False,
    )
    if header_name.lower() in reserved_headers:
        raise ConfigurationError(
            f"api_key_header_name cannot override runtime-managed headers: {header_name}"
        )


def _ensure_headers_are_non_sensitive(extra_headers: dict[str, str]) -> None:
    sensitive_headers = [
        header_name for header_name in extra_headers if _looks_like_sensitive_header_name(header_name)
    ]
    if sensitive_headers:
        headers_text = ", ".join(sorted(sensitive_headers, key=str.lower))
        raise ConfigurationError(
            "extra_headers only support non-sensitive metadata headers. "
            "Use auth_strategy/api_key_header_name for authentication headers: "
            f"{headers_text}"
        )


def _build_runtime_reserved_headers(
    *,
    api_dialect: str,
    auth_strategy: str | None,
    api_key_header_name: str | None,
    include_auth_header: bool = True,
) -> set[str]:
    reserved_headers = {CONTENT_TYPE_HEADER_NAME}
    reserved_headers.add(USER_AGENT_HEADER_NAME)
    if normalize_api_dialect(api_dialect) == "anthropic_messages":
        reserved_headers.add(ANTHROPIC_VERSION_HEADER_NAME)
    if not include_auth_header:
        return reserved_headers
    if resolve_auth_strategy(api_dialect, auth_strategy) == "bearer":
        reserved_headers.add("authorization")
    auth_header_name = resolve_api_key_header_name(
        api_dialect=api_dialect,
        auth_strategy=auth_strategy,
        api_key_header_name=api_key_header_name,
    )
    if auth_header_name is not None:
        reserved_headers.add(auth_header_name.lower())
    return reserved_headers


def _looks_like_sensitive_header_name(header_name: str) -> bool:
    normalized = header_name.lower()
    if normalized in SENSITIVE_EXTRA_HEADER_NAMES:
        return True
    return any(fragment in normalized for fragment in SENSITIVE_EXTRA_HEADER_FRAGMENTS)


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
