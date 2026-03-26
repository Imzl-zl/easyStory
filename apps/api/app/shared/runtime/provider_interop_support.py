from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .errors import ConfigurationError
from .llm_protocol import (
    LLMConnection,
    LLMGenerateRequest,
    PreparedLLMHttpRequest,
    build_verification_request,
    normalize_api_dialect,
    normalize_auth_strategy,
    prepare_generation_request,
    resolve_api_key_header_name,
    resolve_model_name,
)
from .provider_interop_config_support import (
    _load_json_file,
    _optional_positive_int,
    _optional_profile_headers,
    _optional_profile_string,
    _prune_timestamps,
    _require_profile_string,
    _to_path,
    _write_json_file,
)

DEFAULT_PROVIDER_INTEROP_CONFIG_PATH = Path(".runtime/provider-interop.local.json")
DEFAULT_PROVIDER_INTEROP_ENV_PATH = Path(".env.provider-interop.local")
DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH = Path(".runtime/provider-interop.rate-limit.json")
RATE_LIMIT_WINDOW_SECONDS = 60
PROBE_MAX_TOKENS = 256
GEMINI_MINIMAL_THINKING_LEVEL = "minimal"


@dataclass(frozen=True)
class ProviderInteropProfile:
    id: str
    provider: str
    api_dialect: str
    base_url: str | None
    default_model: str | None
    api_key_env: str
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
    payload = _load_json_file(_to_path(config_path))
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
        ),
        max_requests_per_minute=profile.max_requests_per_minute,
        notes=profile.notes,
    )


def build_provider_interop_probe_request(
    profile: ResolvedProviderInteropProfile,
    *,
    prompt: str | None = None,
    system_prompt: str | None = None,
):
    if prompt is not None:
        request = prepare_generation_request(
            LLMGenerateRequest(
                connection=profile.connection,
                model_name=profile.model_name,
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=0.0,
                max_tokens=PROBE_MAX_TOKENS,
                top_p=1.0,
            )
        )
        if profile.connection.api_dialect == "gemini_generate_content":
            return _apply_gemini_probe_thinking_config(request, profile.model_name)
        return request
    return build_verification_request(profile.connection)


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
    path = _to_path(rate_limit_path)
    state = _load_rate_limit_state(path)
    threshold = current_timestamp - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _prune_timestamps(state.get(profile_id, []), threshold)
    if len(timestamps) >= max_requests_per_minute:
        raise ConfigurationError(
            f"Local rate limit exceeded for profile '{profile_id}': "
            f"{max_requests_per_minute} requests in the last {RATE_LIMIT_WINDOW_SECONDS} seconds"
        )
    timestamps.append(current_timestamp)
    state[profile_id] = timestamps
    _write_json_file(path, state)


def _parse_profile(raw_profile: Any) -> ProviderInteropProfile:
    if not isinstance(raw_profile, dict):
        raise ConfigurationError("provider interop profile must be an object")
    return ProviderInteropProfile(
        id=_require_profile_string(raw_profile, "id"),
        provider=_require_profile_string(raw_profile, "provider"),
        api_dialect=normalize_api_dialect(_require_profile_string(raw_profile, "api_dialect")),
        base_url=_optional_profile_string(raw_profile.get("base_url")),
        default_model=_optional_profile_string(raw_profile.get("default_model")),
        api_key_env=_require_profile_string(raw_profile, "api_key_env"),
        auth_strategy=normalize_auth_strategy(_optional_profile_string(raw_profile.get("auth_strategy"))),
        api_key_header_name=_optional_profile_string(raw_profile.get("api_key_header_name")),
        extra_headers=_optional_profile_headers(raw_profile.get("extra_headers")),
        max_requests_per_minute=_optional_positive_int(raw_profile.get("max_requests_per_minute")),
        notes=_optional_profile_string(raw_profile.get("notes")),
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
    merged.update(_optional_profile_headers(override.extra_headers) or {})
    return merged or None


def _resolve_api_key(api_key_env: str, env_values: dict[str, str | None]) -> str:
    value = os.environ.get(api_key_env) or env_values.get(api_key_env)
    if value is None or not value.strip():
        raise ConfigurationError(f"Missing API key value for env var: {api_key_env}")
    return value.strip()


def _apply_gemini_probe_thinking_config(
    request: PreparedLLMHttpRequest,
    model_name: str,
) -> PreparedLLMHttpRequest:
    body = dict(request.json_body)
    generation_config = dict(body.get("generationConfig") or {})
    generation_config["thinkingConfig"] = _build_gemini_probe_thinking_config(model_name)
    body["generationConfig"] = generation_config
    return PreparedLLMHttpRequest(
        method=request.method,
        url=request.url,
        headers=request.headers,
        json_body=body,
    )


def _build_gemini_probe_thinking_config(model_name: str) -> dict[str, int | str]:
    if "2.5" in model_name.lower():
        return {"thinkingBudget": 0}
    return {"thinkingLevel": GEMINI_MINIMAL_THINKING_LEVEL}


def _load_env_values(env_path: str | Path) -> dict[str, str | None]:
    path = _to_path(env_path)
    if not path.exists():
        return {}
    values = dotenv_values(path)
    return {key: value for key, value in values.items()}


def _load_rate_limit_state(path: Path) -> dict[str, list[int]]:
    if not path.exists():
        return {}
    payload = _load_json_file(path)
    state: dict[str, list[int]] = {}
    for profile_id, timestamps in payload.items():
        if isinstance(profile_id, str) and isinstance(timestamps, list):
            state[profile_id] = [timestamp for timestamp in timestamps if isinstance(timestamp, int)]
    return state
