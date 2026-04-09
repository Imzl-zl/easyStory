from .llm_endpoint_policy import normalize_custom_base_url
from .llm_interop_profiles import (
    LLMInteropCapabilities,
    LlmInteropProfile,
    normalize_interop_profile,
    resolve_default_interop_profile,
    resolve_interop_capabilities,
)
from .llm_protocol_requests import build_verification_request, prepare_generation_request
from .llm_protocol_responses import parse_generation_response
from .llm_protocol_types import (
    ANTHROPIC_VERSION,
    DEFAULT_API_DIALECT,
    DEFAULT_AUTH_STRATEGY_BY_DIALECT,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    GeminiThinkingLevel,
    HttpJsonResponse,
    LLMContinuationSupport,
    LLMFunctionToolDefinition,
    JSON_OBJECT_RESPONSE_FORMAT,
    LLMConnection,
    LLMGenerateRequest,
    LlmApiDialect,
    LlmAuthStrategy,
    LlmContinuationMode,
    LlmRuntimeKind,
    NormalizedLLMResponse,
    OpenAIReasoningEffort,
    PreparedLLMHttpRequest,
    VERIFY_MAX_TOKENS,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
    allows_provider_continuation_state,
    normalize_api_dialect,
    normalize_auth_strategy,
    normalize_http_header_name,
    normalize_runtime_kind,
    resolve_api_key_header_name,
    resolve_auth_strategy,
    resolve_continuation_support,
    resolve_model_name,
    send_json_http_request,
)


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

__all__ = [
    "ANTHROPIC_VERSION",
    "DEFAULT_API_DIALECT",
    "DEFAULT_AUTH_STRATEGY_BY_DIALECT",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "GeminiThinkingLevel",
    "HttpJsonResponse",
    "LLMContinuationSupport",
    "LLMFunctionToolDefinition",
    "JSON_OBJECT_RESPONSE_FORMAT",
    "LLMInteropCapabilities",
    "LLMConnection",
    "LLMGenerateRequest",
    "LlmApiDialect",
    "LlmAuthStrategy",
    "LlmContinuationMode",
    "LlmInteropProfile",
    "LlmRuntimeKind",
    "NormalizedLLMResponse",
    "OpenAIReasoningEffort",
    "PreparedLLMHttpRequest",
    "VERIFY_MAX_TOKENS",
    "VERIFY_SYSTEM_PROMPT",
    "VERIFY_USER_PROMPT",
    "allows_provider_continuation_state",
    "build_verification_request",
    "normalize_api_dialect",
    "normalize_auth_strategy",
    "normalize_http_header_name",
    "normalize_interop_profile",
    "normalize_runtime_kind",
    "normalize_custom_base_url",
    "parse_generation_response",
    "prepare_generation_request",
    "resolve_default_interop_profile",
    "resolve_api_key_header_name",
    "resolve_auth_strategy",
    "resolve_connection_continuation_support",
    "resolve_continuation_support",
    "resolve_interop_capabilities",
    "resolve_model_name",
    "send_json_http_request",
]
