from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from .errors import ConfigurationError

LlmApiDialect = Literal[
    "openai_chat_completions",
    "openai_responses",
    "anthropic_messages",
    "gemini_generate_content",
]

DEFAULT_API_DIALECT: LlmApiDialect = "openai_chat_completions"
SUPPORTED_API_DIALECTS = frozenset(
    {
        "openai_chat_completions",
        "openai_responses",
        "anthropic_messages",
        "gemini_generate_content",
    }
)
DEFAULT_BASE_URLS: dict[LlmApiDialect, str] = {
    "openai_chat_completions": "https://api.openai.com",
    "openai_responses": "https://api.openai.com",
    "anthropic_messages": "https://api.anthropic.com",
    "gemini_generate_content": "https://generativelanguage.googleapis.com",
}
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
VERIFY_MODEL_REPLY = "Reply with ok."
JSON_OBJECT_RESPONSE_FORMAT = "json_object"


@dataclass(frozen=True)
class LLMConnection:
    api_dialect: LlmApiDialect
    api_key: str
    base_url: str | None
    default_model: str | None = None


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
