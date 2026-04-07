from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..errors import ConfigurationError
from .llm_protocol_types import normalize_api_dialect

LlmInteropProfile = Literal[
    "responses_strict",
    "responses_delta_first_terminal_empty_output",
    "chat_compat_plain",
    "chat_compat_reasoning_content",
    "chat_compat_usage_extra_chunk",
]

SUPPORTED_INTEROP_PROFILES = frozenset(
    {
        "responses_strict",
        "responses_delta_first_terminal_empty_output",
        "chat_compat_plain",
        "chat_compat_reasoning_content",
        "chat_compat_usage_extra_chunk",
    }
)

DEFAULT_INTEROP_PROFILE_BY_DIALECT = {
    "openai_responses": "responses_delta_first_terminal_empty_output",
    "openai_chat_completions": "chat_compat_plain",
}


@dataclass(frozen=True)
class LLMInteropCapabilities:
    profile: LlmInteropProfile | None
    allows_responses_empty_output_in_stream_terminal: bool = False
    captures_chat_reasoning_content: bool = False
    expects_chat_usage_extra_chunk: bool = False


def normalize_interop_profile(interop_profile: str | None) -> LlmInteropProfile | None:
    if interop_profile is None:
        return None
    normalized = interop_profile.strip()
    if not normalized:
        return None
    if normalized not in SUPPORTED_INTEROP_PROFILES:
        raise ConfigurationError(f"Unsupported interop_profile: {interop_profile}")
    return normalized  # type: ignore[return-value]


def resolve_interop_capabilities(
    api_dialect: str,
    interop_profile: str | None = None,
) -> LLMInteropCapabilities:
    dialect = normalize_api_dialect(api_dialect)
    normalized_profile = normalize_interop_profile(interop_profile)
    if normalized_profile is None:
        normalized_profile = DEFAULT_INTEROP_PROFILE_BY_DIALECT.get(dialect)
    if dialect == "openai_responses":
        return _resolve_responses_capabilities(normalized_profile)
    if dialect == "openai_chat_completions":
        return _resolve_chat_capabilities(normalized_profile)
    if normalized_profile is not None:
        raise ConfigurationError(
            f"interop_profile '{normalized_profile}' is not supported for api_dialect '{dialect}'"
        )
    return LLMInteropCapabilities(profile=None)


def _resolve_responses_capabilities(
    interop_profile: LlmInteropProfile | None,
) -> LLMInteropCapabilities:
    if interop_profile not in {
        "responses_strict",
        "responses_delta_first_terminal_empty_output",
    }:
        raise ConfigurationError(
            "openai_responses 只支持 responses_strict 或 "
            "responses_delta_first_terminal_empty_output interop_profile"
        )
    return LLMInteropCapabilities(
        profile=interop_profile,
        allows_responses_empty_output_in_stream_terminal=(
            interop_profile == "responses_delta_first_terminal_empty_output"
        ),
    )


def _resolve_chat_capabilities(
    interop_profile: LlmInteropProfile | None,
) -> LLMInteropCapabilities:
    if interop_profile not in {
        "chat_compat_plain",
        "chat_compat_reasoning_content",
        "chat_compat_usage_extra_chunk",
    }:
        raise ConfigurationError(
            "openai_chat_completions 只支持 chat_compat_plain / "
            "chat_compat_reasoning_content / chat_compat_usage_extra_chunk interop_profile"
        )
    return LLMInteropCapabilities(
        profile=interop_profile,
        captures_chat_reasoning_content=(interop_profile == "chat_compat_reasoning_content"),
        expects_chat_usage_extra_chunk=(interop_profile == "chat_compat_usage_extra_chunk"),
    )
