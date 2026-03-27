from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal

import httpx

from .errors import ConfigurationError

LlmApiDialect = Literal[
    "openai_chat_completions",
    "openai_responses",
    "anthropic_messages",
    "gemini_generate_content",
]
LlmAuthStrategy = Literal["bearer", "x_api_key", "x_goog_api_key", "custom_header"]

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
DEFAULT_BASE_URLS: dict[LlmApiDialect, str] = {
    "openai_chat_completions": "https://api.openai.com",
    "openai_responses": "https://api.openai.com",
    "anthropic_messages": "https://api.anthropic.com",
    "gemini_generate_content": "https://generativelanguage.googleapis.com",
}
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
VERIFY_MODEL_REPLY = "今天天气真好。"
VERIFY_USER_PROMPT = (
    "这是一次模型连接验证。请只回复这句话，不要添加额外内容：今天天气真好。"
)
VERIFY_SYSTEM_PROMPT = (
    "你正在执行模型连接验证。请严格按要求回复，不要添加解释、标点变化或额外文本。"
)
VERIFY_MAX_TOKENS = 32
JSON_OBJECT_RESPONSE_FORMAT = "json_object"
HTTP_HEADER_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


@dataclass(frozen=True)
class LLMConnection:
    api_dialect: LlmApiDialect
    api_key: str
    base_url: str | None
    default_model: str | None = None
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = None
    extra_headers: dict[str, str] | None = None


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
    stop: list[str] | None = None


@dataclass(frozen=True)
class PreparedLLMHttpRequest:
    method: str
    url: str
    headers: dict[str, str]
    json_body: dict[str, Any]


@dataclass(frozen=True)
class HttpJsonResponse:
    status_code: int
    json_body: dict[str, Any] | None
    text: str


@dataclass(frozen=True)
class NormalizedLLMResponse:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


def normalize_api_dialect(api_dialect: str | None) -> LlmApiDialect:
    if api_dialect is None:
        return DEFAULT_API_DIALECT
    normalized = api_dialect.strip()
    if normalized not in SUPPORTED_API_DIALECTS:
        raise ConfigurationError(f"Unsupported api_dialect: {api_dialect}")
    return normalized  # type: ignore[return-value]


def normalize_auth_strategy(auth_strategy: str | None) -> LlmAuthStrategy | None:
    normalized = _normalize_optional_string(auth_strategy)
    if normalized is None:
        return None
    if normalized not in SUPPORTED_AUTH_STRATEGIES:
        raise ConfigurationError(f"Unsupported auth_strategy: {auth_strategy}")
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
