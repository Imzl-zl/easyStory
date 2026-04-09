from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Literal

import httpx

from ..errors import ConfigurationError

LlmApiDialect = Literal[
    "openai_chat_completions",
    "openai_responses",
    "anthropic_messages",
    "gemini_generate_content",
]
LlmAuthStrategy = Literal["bearer", "x_api_key", "x_goog_api_key", "custom_header"]
LlmRuntimeKind = Literal["server-python", "server-node", "browser"]
LlmContinuationMode = Literal["provider_continuation", "runtime_replay", "hybrid"]
OpenAIReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
GeminiThinkingLevel = Literal["minimal", "low", "medium", "high"]

DEFAULT_API_DIALECT: LlmApiDialect = "openai_chat_completions"
DEFAULT_AUTH_STRATEGY_BY_DIALECT: dict[LlmApiDialect, LlmAuthStrategy] = {
    "openai_chat_completions": "bearer",
    "openai_responses": "bearer",
    "anthropic_messages": "x_api_key",
    "gemini_generate_content": "x_goog_api_key",
}
DEFAULT_API_KEY_HEADER_NAMES: dict[LlmAuthStrategy, str] = {
    "x_api_key": "x-api-key",
    "x_goog_api_key": "x-goog-api-key",
    "custom_header": "",
    "bearer": "",
}
SUPPORTED_API_DIALECTS = frozenset(
    {
        "openai_chat_completions",
        "openai_responses",
        "anthropic_messages",
        "gemini_generate_content",
    }
)
SUPPORTED_AUTH_STRATEGIES = frozenset({"bearer", "x_api_key", "x_goog_api_key", "custom_header"})
SUPPORTED_RUNTIME_KINDS = frozenset({"server-python", "server-node", "browser"})
DEFAULT_BASE_URLS: dict[LlmApiDialect, str] = {
    "openai_chat_completions": "https://api.openai.com",
    "openai_responses": "https://api.openai.com",
    "anthropic_messages": "https://api.anthropic.com",
    "gemini_generate_content": "https://generativelanguage.googleapis.com",
}
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
VERIFY_USER_PROMPT = (
    "今天天气怎么样？"
)
VERIFY_SYSTEM_PROMPT = (
    "请像日常聊天一样，用一句简短中文直接回答用户问题，不要使用 Markdown。"
)
# Verification requests should not use tiny output budgets. Reasoning-capable
# models may spend part of the allowance before producing visible output, which
# turns credential checks into false negatives.
VERIFY_MAX_TOKENS = 256
JSON_OBJECT_RESPONSE_FORMAT = "json_object"
HTTP_HEADER_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


@dataclass(frozen=True)
class LLMContinuationSupport:
    continuation_mode: LlmContinuationMode
    tolerates_interleaved_tool_results: bool
    requires_full_replay_after_local_tools: bool


@dataclass(frozen=True)
class LLMConnection:
    api_dialect: LlmApiDialect
    api_key: str
    base_url: str | None
    default_model: str | None = None
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = None
    extra_headers: dict[str, str] | None = None
    user_agent_override: str | None = None
    client_name: str | None = None
    client_version: str | None = None
    runtime_kind: LlmRuntimeKind | None = None
    interop_profile: str | None = None
    provider: str | None = None


@dataclass(frozen=True)
class LLMGenerateRequest:
    connection: LLMConnection
    model_name: str
    prompt: str
    system_prompt: str | None
    response_format: str
    temperature: float | None
    max_tokens: int | None
    top_p: float | None
    reasoning_effort: OpenAIReasoningEffort | None = None
    thinking_level: GeminiThinkingLevel | None = None
    thinking_budget: int | None = None
    stop: list[str] | None = None
    tools: list["LLMFunctionToolDefinition"] = field(default_factory=list)
    continuation_items: list[dict[str, Any]] = field(default_factory=list)
    provider_continuation_state: dict[str, Any] | None = None
    force_tool_call: bool = False


@dataclass(frozen=True)
class PreparedLLMHttpRequest:
    method: str
    url: str
    headers: dict[str, str]
    json_body: dict[str, Any]
    interop_profile: str | None = None
    tool_name_aliases: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HttpJsonResponse:
    status_code: int
    json_body: dict[str, Any] | None
    text: str


@dataclass(frozen=True)
class LLMFunctionToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool = True


@dataclass(frozen=True)
class NormalizedLLMToolCall:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    arguments_text: str | None = None
    arguments_error: str | None = None
    provider_ref: str | None = None
    provider_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class NormalizedLLMResponse:
    content: str
    finish_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    tool_calls: list[NormalizedLLMToolCall] = field(default_factory=list)
    provider_response_id: str | None = None
    provider_output_items: list[dict[str, Any]] = field(default_factory=list)


def normalize_api_dialect(api_dialect: str | None) -> LlmApiDialect:
    if api_dialect is None:
        return DEFAULT_API_DIALECT
    normalized = api_dialect.strip()
    if normalized not in SUPPORTED_API_DIALECTS:
        raise ConfigurationError(f"Unsupported api_dialect: {api_dialect}")
    return normalized  # type: ignore[return-value]


def resolve_continuation_support(api_dialect: str | None) -> LLMContinuationSupport:
    dialect = normalize_api_dialect(api_dialect)
    if dialect == "openai_responses":
        return LLMContinuationSupport(
            continuation_mode="hybrid",
            tolerates_interleaved_tool_results=True,
            requires_full_replay_after_local_tools=False,
        )
    return LLMContinuationSupport(
        continuation_mode="runtime_replay",
        tolerates_interleaved_tool_results=False,
        requires_full_replay_after_local_tools=True,
    )


def allows_provider_continuation_state(continuation_support: LLMContinuationSupport) -> bool:
    return continuation_support.continuation_mode != "runtime_replay"


def normalize_auth_strategy(auth_strategy: str | None) -> LlmAuthStrategy | None:
    normalized = _normalize_optional_string(auth_strategy)
    if normalized is None:
        return None
    if normalized not in SUPPORTED_AUTH_STRATEGIES:
        raise ConfigurationError(f"Unsupported auth_strategy: {auth_strategy}")
    return normalized  # type: ignore[return-value]


def normalize_runtime_kind(runtime_kind: str | None) -> LlmRuntimeKind | None:
    normalized = _normalize_optional_string(runtime_kind)
    if normalized is None:
        return None
    if normalized not in SUPPORTED_RUNTIME_KINDS:
        raise ConfigurationError(f"Unsupported runtime_kind: {runtime_kind}")
    return normalized  # type: ignore[return-value]


def resolve_auth_strategy(api_dialect: str | None, auth_strategy: str | None) -> LlmAuthStrategy:
    explicit_strategy = normalize_auth_strategy(auth_strategy)
    if explicit_strategy is not None:
        return explicit_strategy
    dialect = normalize_api_dialect(api_dialect)
    return DEFAULT_AUTH_STRATEGY_BY_DIALECT[dialect]


def resolve_api_key_header_name(
    *,
    api_dialect: str | None,
    auth_strategy: str | None,
    api_key_header_name: str | None,
) -> str | None:
    strategy = resolve_auth_strategy(api_dialect, auth_strategy)
    normalized_name = _normalize_http_header_name(api_key_header_name)
    if strategy == "bearer":
        if normalized_name is not None:
            raise ConfigurationError("api_key_header_name is only supported with non-bearer auth_strategy")
        return None
    if strategy == "custom_header":
        if normalized_name is None:
            raise ConfigurationError("custom_header auth_strategy requires api_key_header_name")
        return normalized_name
    default_name = DEFAULT_API_KEY_HEADER_NAMES[strategy]
    if normalized_name is not None and normalized_name.lower() != default_name:
        raise ConfigurationError(
            f"api_key_header_name is not supported for auth_strategy '{strategy}'"
        )
    return default_name


def normalize_http_header_name(header_name: str | None) -> str | None:
    return _normalize_http_header_name(header_name)


def resolve_model_name(
    requested_model_name: str | None,
    default_model: str | None,
    *,
    provider_label: str,
) -> str:
    explicit = _normalize_optional_string(requested_model_name)
    if explicit is not None:
        return explicit
    fallback = _normalize_optional_string(default_model)
    if fallback is not None:
        return fallback
    raise ConfigurationError(f"Provider '{provider_label}' is missing executable model name")


async def send_json_http_request(
    request: PreparedLLMHttpRequest,
    *,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> HttpJsonResponse:
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.request(
            request.method,
            request.url,
            headers=request.headers,
            json=request.json_body,
        )
    return HttpJsonResponse(
        status_code=response.status_code,
        json_body=_read_json_body(response),
        text=response.text,
    )


def _read_json_body(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_http_header_name(header_name: str | None) -> str | None:
    normalized = _normalize_optional_string(header_name)
    if normalized is None:
        return None
    if HTTP_HEADER_TOKEN_PATTERN.fullmatch(normalized) is None:
        raise ConfigurationError("api_key_header_name must be a valid HTTP header name")
    return normalized
