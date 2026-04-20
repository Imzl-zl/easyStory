from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..errors import ConfigurationError
from .interop.tool_schema_compiler import ToolSchemaMode
from .interop.tool_name_codec import ToolNamePolicy
from .llm_protocol_types import (
    LLMContinuationSupport,
    normalize_api_dialect,
    resolve_continuation_support,
)

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
    """只保留当前 runtime 已有消费点的 capability 字段，避免长空壳结构。"""

    profile: LlmInteropProfile | None
    tool_name_policy: ToolNamePolicy = "safe_ascii_only"
    tool_schema_mode: ToolSchemaMode = "portable_subset"
    supports_parallel_tool_calls: bool = False
    supports_provider_response_continuation: bool = False
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


def resolve_default_interop_profile(api_dialect: str) -> LlmInteropProfile | None:
    dialect = normalize_api_dialect(api_dialect)
    return DEFAULT_INTEROP_PROFILE_BY_DIALECT.get(dialect)


def resolve_interop_capabilities(
    api_dialect: str,
    interop_profile: str | None = None,
) -> LLMInteropCapabilities:
    dialect = normalize_api_dialect(api_dialect)
    normalized_profile = normalize_interop_profile(interop_profile)
    if normalized_profile is None:
        normalized_profile = resolve_default_interop_profile(dialect)
    if dialect == "openai_responses":
        return _resolve_responses_capabilities(normalized_profile)
    if dialect == "openai_chat_completions":
        return _resolve_chat_capabilities(normalized_profile)
    if normalized_profile is not None:
        raise ConfigurationError(
            f"interop_profile '{normalized_profile}' is not supported for api_dialect '{dialect}'"
        )
    if dialect == "anthropic_messages":
        return LLMInteropCapabilities(profile=None, tool_schema_mode="portable_subset")
    if dialect == "gemini_generate_content":
        return LLMInteropCapabilities(profile=None, tool_schema_mode="gemini_compatible")
    raise ConfigurationError(f"Unsupported api_dialect for interop capabilities: {dialect}")


def resolve_connection_continuation_support(
    api_dialect: str | None,
    interop_profile: str | None = None,
) -> LLMContinuationSupport:
    support = resolve_continuation_support(api_dialect)
    if normalize_api_dialect(api_dialect) != "openai_responses":
        return support
    capabilities = resolve_interop_capabilities(
        api_dialect,
        interop_profile,
    )
    if capabilities.supports_provider_response_continuation:
        return support
    return LLMContinuationSupport(
        continuation_mode="runtime_replay",
        tolerates_interleaved_tool_results=False,
        requires_full_replay_after_local_tools=True,
    )


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
        tool_schema_mode="openai_strict_compatible",
        supports_provider_response_continuation=(interop_profile == "responses_strict"),
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
        tool_schema_mode="openai_strict_compatible",
        captures_chat_reasoning_content=(interop_profile == "chat_compat_reasoning_content"),
        expects_chat_usage_extra_chunk=(interop_profile == "chat_compat_usage_extra_chunk"),
    )
