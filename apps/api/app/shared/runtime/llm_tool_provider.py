from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from . import provider_interop_stream_support as stream_support
from .errors import ConfigurationError
from .llm_protocol import (
    HttpJsonResponse,
    LLMConnection,
    LLMGenerateRequest,
    PreparedLLMHttpRequest,
    normalize_api_dialect,
    normalize_auth_strategy,
    parse_generation_response,
    prepare_generation_request,
    resolve_model_name,
    send_json_http_request,
)
from .tool_provider import ToolProvider

LLM_GENERATE_TOOL = "llm.generate"


class AsyncLlmRequestSender(Protocol):
    async def __call__(self, request: PreparedLLMHttpRequest) -> HttpJsonResponse: ...


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    model_name: str
    provider: str | None
    system_prompt: str | None
    response_format: str
    temperature: float | None
    max_tokens: int | None
    top_p: float | None
    stop: list[str] | None
    connection: LLMConnection


@dataclass(frozen=True)
class LLMStreamEvent:
    delta: str | None = None
    response: dict[str, Any] | None = None


class LLMToolProvider(ToolProvider):
    def __init__(
        self,
        *,
        request_sender: AsyncLlmRequestSender | None = None,
    ) -> None:
        self.request_sender = request_sender or _default_request_sender

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name != LLM_GENERATE_TOOL:
            raise ConfigurationError(f"Unsupported tool: {tool_name}")
        request = _build_request(params)
        response = await self.request_sender(prepare_generation_request(_to_generate_request(request)))
        if response.status_code >= 400:
            raise ConfigurationError(_build_http_error_message(response))
        normalized = parse_generation_response(request.connection.api_dialect, response.json_body or {})
        return {
            "content": normalized.content,
            "model_name": request.model_name,
            "provider": request.provider,
            "input_tokens": normalized.input_tokens,
            "output_tokens": normalized.output_tokens,
            "total_tokens": normalized.total_tokens,
        }

    async def execute_stream(
        self,
        tool_name: str,
        params: dict[str, Any],
        *,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        if tool_name != LLM_GENERATE_TOOL:
            raise ConfigurationError(f"Unsupported tool: {tool_name}")
        request = _build_request(params)
        prepared_request = stream_support.build_stream_probe_request(
            prepare_generation_request(_to_generate_request(request)),
            api_dialect=request.connection.api_dialect,
        )
        parts: list[str] = []
        truncation_reason: str | None = None
        async for event in stream_support.iterate_stream_request(
            prepared_request,
            api_dialect=request.connection.api_dialect,
            should_stop=should_stop,
        ):
            if truncation_reason is None:
                truncation_reason = stream_support.extract_stream_truncation_reason(event.stop_reason)
            if not event.delta:
                continue
            parts.append(event.delta)
            yield LLMStreamEvent(delta=event.delta)
        content = "".join(parts)
        if not content:
            raise ConfigurationError("模型没有返回可展示的内容，请稍后重试。")
        if truncation_reason is not None:
            raise ConfigurationError(
                stream_support.build_truncated_stream_message(truncation_reason)
            )
        yield LLMStreamEvent(
            response={
                "content": content,
                "model_name": request.model_name,
                "provider": request.provider,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            }
        )

    def list_tools(self) -> list[str]:
        return [LLM_GENERATE_TOOL]


def _build_request(params: dict[str, Any]) -> LLMRequest:
    prompt = _require_non_empty_string(params.get("prompt"), "prompt")
    model = _require_dict(params.get("model"), "model")
    credential = _require_dict(params.get("credential"), "credential")
    provider = _optional_string(model.get("provider"))
    model_name = resolve_model_name(
        requested_model_name=_optional_string(model.get("name")),
        default_model=_optional_string(credential.get("default_model")),
        provider_label=provider or "credential",
    )
    return LLMRequest(
        prompt=prompt,
        model_name=model_name,
        provider=provider,
        system_prompt=_optional_string(params.get("system_prompt")),
        response_format=_optional_string(params.get("response_format")) or "text",
        temperature=_optional_float(model.get("temperature")),
        max_tokens=_resolve_max_tokens(
            requested_value=model.get("max_tokens"),
            default_value=credential.get("default_max_output_tokens"),
        ),
        top_p=_optional_float(model.get("top_p")),
        stop=_optional_string_list(model.get("stop")),
        connection=_build_connection(credential),
    )


def _to_generate_request(request: LLMRequest) -> LLMGenerateRequest:
    return LLMGenerateRequest(
        connection=request.connection,
        model_name=request.model_name,
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        response_format=request.response_format,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        stop=request.stop,
    )


def _build_http_error_message(response: HttpJsonResponse) -> str:
    if response.json_body is not None:
        error = response.json_body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return f"LLM request failed: HTTP {response.status_code} - {error['message']}"
        if isinstance(error, str):
            return f"LLM request failed: HTTP {response.status_code} - {error}"
    suffix = response.text.strip()
    if suffix:
        return f"LLM request failed: HTTP {response.status_code} - {suffix}"
    return f"LLM request failed: HTTP {response.status_code}"


def _build_connection(credential: dict[str, Any]) -> LLMConnection:
    return LLMConnection(
        api_dialect=normalize_api_dialect(_optional_string(credential.get("api_dialect"))),
        api_key=_require_non_empty_string(credential.get("api_key"), "credential.api_key"),
        base_url=_optional_string(credential.get("base_url")),
        default_model=_optional_string(credential.get("default_model")),
        auth_strategy=normalize_auth_strategy(_optional_string(credential.get("auth_strategy"))),
        api_key_header_name=_optional_string(credential.get("api_key_header_name")),
        extra_headers=_optional_string_mapping(credential.get("extra_headers")),
    )


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field_name} must be an object")
    return value


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("Expected string value")
    stripped = value.strip()
    return stripped or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError("Expected numeric value")
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError("Expected integer value")
    return value


def _resolve_max_tokens(*, requested_value: Any, default_value: Any) -> int | None:
    requested_max_tokens = _optional_int(requested_value)
    if requested_max_tokens is not None:
        return requested_max_tokens
    return _optional_int(default_value)


def _optional_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ConfigurationError("Expected string list value")
    normalized: list[str] = []
    for item in value:
        normalized_item = _require_non_empty_string(item, "string_list_item")
        normalized.append(normalized_item)
    return normalized or None


def _optional_string_mapping(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError("Expected string mapping value")
    normalized: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = _require_non_empty_string(raw_key, "string_mapping_key")
        mapped_value = _require_non_empty_string(raw_value, f"string_mapping[{key}]")
        normalized[key] = mapped_value
    return normalized or None


async def _default_request_sender(request: PreparedLLMHttpRequest) -> HttpJsonResponse:
    return await send_json_http_request(request)
