from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from ...errors import ConfigurationError
from ..llm_interop_profiles import normalize_interop_profile
from ..llm_protocol import (
    LLMConnection,
    normalize_api_dialect,
    normalize_auth_strategy,
    resolve_api_key_header_name,
    resolve_model_name,
)
from .provider_interop_config_support import (
    load_json_file,
    optional_positive_int,
    optional_profile_headers,
    optional_profile_string,
    prune_timestamps,
    require_profile_string,
    to_path,
    write_json_file,
)

DEFAULT_PROVIDER_INTEROP_CONFIG_PATH = Path(".runtime/provider-interop.local.json")
DEFAULT_PROVIDER_INTEROP_ENV_PATH = Path(".env.provider-interop.local")
DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH = Path(".runtime/provider-interop.rate-limit.json")
RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class ProviderInteropProfile:
    id: str
    provider: str
    api_dialect: str
    base_url: str | None
    default_model: str | None
    api_key_env: str
    interop_profile: str | None = None
    auth_strategy: str | None = None
    api_key_header_name: str | None = None
    extra_headers: dict[str, str] | None = None
    max_requests_per_minute: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ProviderInteropOverride:
    api_dialect: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    interop_profile: str | None = None
    auth_strategy: str | None = None
    api_key_header_name: str | None = None
    extra_headers: dict[str, str] | None = None


@dataclass(frozen=True)
class ResolvedProviderInteropProfile:
    profile_id: str
    provider: str
    model_name: str
    connection: LLMConnection
    max_requests_per_minute: int | None
    notes: str | None


def load_provider_interop_profiles(
    config_path: str | Path = DEFAULT_PROVIDER_INTEROP_CONFIG_PATH,
) -> list[ProviderInteropProfile]:
    payload = load_json_file(to_path(config_path))
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ConfigurationError("provider interop config must contain a 'profiles' array")
    profiles = [_parse_profile(item) for item in raw_profiles]
    _ensure_unique_profile_ids(profiles)
    return profiles


def resolve_provider_interop_profile(
    profile_id: str,
    *,
    config_path: str | Path = DEFAULT_PROVIDER_INTEROP_CONFIG_PATH,
    env_path: str | Path = DEFAULT_PROVIDER_INTEROP_ENV_PATH,
    override: ProviderInteropOverride | None = None,
) -> ResolvedProviderInteropProfile:
    profile = _find_profile(profile_id, load_provider_interop_profiles(config_path))
    active_override = override or ProviderInteropOverride()
    api_key = _resolve_api_key(profile.api_key_env, _load_env_values(env_path))
    api_dialect = normalize_api_dialect(active_override.api_dialect or profile.api_dialect)
    auth_strategy = normalize_auth_strategy(active_override.auth_strategy or profile.auth_strategy)
    header_name = _resolve_header_name(profile, active_override)
    model_name = resolve_model_name(
        requested_model_name=active_override.model_name,
        default_model=profile.default_model,
        provider_label=profile.id,
    )
    resolve_api_key_header_name(
        api_dialect=api_dialect,
        auth_strategy=auth_strategy,
        api_key_header_name=header_name,
    )
    return ResolvedProviderInteropProfile(
        profile_id=profile.id,
        provider=profile.provider,
        model_name=model_name,
        connection=LLMConnection(
            api_dialect=api_dialect,
            api_key=api_key,
            base_url=active_override.base_url or profile.base_url,
            default_model=model_name,
            auth_strategy=auth_strategy,
            api_key_header_name=header_name,
            extra_headers=_resolve_extra_headers(profile, active_override),
            interop_profile=_resolve_interop_profile(profile, active_override),
        ),
        max_requests_per_minute=profile.max_requests_per_minute,
        notes=profile.notes,
    )


def enforce_provider_interop_rate_limit(
    *,
    profile_id: str,
    max_requests_per_minute: int | None,
    rate_limit_path: str | Path = DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH,
    now_seconds: int | None = None,
) -> None:
    if max_requests_per_minute is None:
        return
    if max_requests_per_minute < 1:
        raise ConfigurationError("max_requests_per_minute must be >= 1")
    current_timestamp = now_seconds or int(time.time())
    path = to_path(rate_limit_path)
    state = _load_rate_limit_state(path)
    threshold = current_timestamp - RATE_LIMIT_WINDOW_SECONDS
    timestamps = prune_timestamps(state.get(profile_id, []), threshold)
    if len(timestamps) >= max_requests_per_minute:
        raise ConfigurationError(
            f"Local rate limit exceeded for profile '{profile_id}': "
            f"{max_requests_per_minute} requests in the last {RATE_LIMIT_WINDOW_SECONDS} seconds"
        )
    timestamps.append(current_timestamp)
    state[profile_id] = timestamps
    write_json_file(path, state)


def _parse_profile(raw_profile) -> ProviderInteropProfile:
    if not isinstance(raw_profile, dict):
        raise ConfigurationError("provider interop profile must be an object")
    return ProviderInteropProfile(
        id=require_profile_string(raw_profile, "id"),
        provider=require_profile_string(raw_profile, "provider"),
        api_dialect=normalize_api_dialect(require_profile_string(raw_profile, "api_dialect")),
        base_url=optional_profile_string(raw_profile.get("base_url")),
        default_model=optional_profile_string(raw_profile.get("default_model")),
        api_key_env=require_profile_string(raw_profile, "api_key_env"),
        interop_profile=normalize_interop_profile(optional_profile_string(raw_profile.get("interop_profile"))),
        auth_strategy=normalize_auth_strategy(optional_profile_string(raw_profile.get("auth_strategy"))),
        api_key_header_name=optional_profile_string(raw_profile.get("api_key_header_name")),
        extra_headers=optional_profile_headers(raw_profile.get("extra_headers")),
        max_requests_per_minute=optional_positive_int(raw_profile.get("max_requests_per_minute")),
        notes=optional_profile_string(raw_profile.get("notes")),
    )


def _ensure_unique_profile_ids(profiles: list[ProviderInteropProfile]) -> None:
    seen: set[str] = set()
    for profile in profiles:
        if profile.id in seen:
            raise ConfigurationError(f"Duplicate provider interop profile id: {profile.id}")
        seen.add(profile.id)


def _find_profile(
    profile_id: str,
    profiles: list[ProviderInteropProfile],
) -> ProviderInteropProfile:
    normalized_id = profile_id.strip()
    for profile in profiles:
        if profile.id == normalized_id:
            return profile
    raise ConfigurationError(f"Unknown provider interop profile: {profile_id}")


def _resolve_header_name(
    profile: ProviderInteropProfile,
    override: ProviderInteropOverride,
) -> str | None:
    if override.api_key_header_name is not None:
        return override.api_key_header_name
    if override.auth_strategy is not None:
        return None
    return profile.api_key_header_name


def _resolve_extra_headers(
    profile: ProviderInteropProfile,
    override: ProviderInteropOverride,
) -> dict[str, str] | None:
    merged = dict(profile.extra_headers or {})
    if override.extra_headers is None:
        return merged or None
    merged.update(optional_profile_headers(override.extra_headers) or {})
    return merged or None


def _resolve_interop_profile(
    profile: ProviderInteropProfile,
    override: ProviderInteropOverride,
) -> str | None:
    if override.interop_profile is not None:
        return normalize_interop_profile(override.interop_profile)
    return profile.interop_profile


def _resolve_api_key(api_key_env: str, env_values: dict[str, str]) -> str:
    value = env_values.get(api_key_env) or os.getenv(api_key_env)
    if value is None or not value.strip():
        raise ConfigurationError(f"Missing API key in env: {api_key_env}")
    return value.strip()


def _load_env_values(env_path: str | Path) -> dict[str, str]:
    path = to_path(env_path)
    if not path.exists():
        return {}
    raw_values = dotenv_values(path)
    return {
        key: value
        for key, value in raw_values.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _load_rate_limit_state(path: Path) -> dict[str, list[int]]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        raise ConfigurationError("provider interop rate-limit state must be an object")
    normalized: dict[str, list[int]] = {}
    for raw_key, raw_value in payload.items():
        if not isinstance(raw_key, str):
            continue
        if not isinstance(raw_value, list):
            continue
        normalized[raw_key] = [item for item in raw_value if isinstance(item, int)]
    return normalized
