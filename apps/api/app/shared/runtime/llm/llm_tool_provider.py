from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from ..errors import ConfigurationError
from ..tool_provider import ToolProvider
from .llm_backend import AsyncLLMGenerateBackend, resolve_backend_selection
from .llm_interop_profiles import normalize_interop_profile
from .llm_protocol import (
    GeminiThinkingLevel,
    LLMConnection,
    LLMContinuationSupport,
    LLMFunctionToolDefinition,
    LLMGenerateRequest,
    NormalizedLLMResponse,
    OpenAIReasoningEffort,
    allows_provider_continuation_state,
    normalize_api_dialect,
    normalize_auth_strategy,
    normalize_runtime_kind,
    resolve_connection_continuation_support,
    resolve_model_name,
)
from .llm_response_validation import raise_if_empty_tool_response
from .litellm_backend import LiteLLMBackend
from .native_http_backend import NativeHttpLLMBackend

LLM_GENERATE_TOOL = "llm.generate"


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
    reasoning_effort: OpenAIReasoningEffort | None
    thinking_level: GeminiThinkingLevel | None
    thinking_budget: int | None
    stop: list[str] | None
    tools: list[LLMFunctionToolDefinition]
    continuation_items: list[dict[str, Any]]
    provider_continuation_state: dict[str, Any] | None
    continuation_support: LLMContinuationSupport
    connection: LLMConnection


@dataclass(frozen=True)
class LLMStreamEvent:
    delta: str | None = None
    response: LLMGenerateToolResponse | None = None


class LLMGenerateToolResponse(TypedDict):
    content: str
    finish_reason: str | None
    model_name: str
    provider: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    tool_calls: list[dict[str, Any]]
    provider_response_id: str | None
    output_items: list[dict[str, Any]]


class LLMToolProvider(ToolProvider):
    def __init__(
        self,
        *,
        request_sender=None,
        backend: AsyncLLMGenerateBackend | None = None,
        native_backend: AsyncLLMGenerateBackend | None = None,
    ) -> None:
        self.default_backend = backend
        self.litellm_backend = backend or LiteLLMBackend()
        self.native_backend = native_backend or NativeHttpLLMBackend(
            request_sender=request_sender,
        )
        self._force_native_backend = request_sender is not None and backend is None

    async def execute(self, tool_name: str, params: dict[str, Any]) -> LLMGenerateToolResponse:
        if tool_name != LLM_GENERATE_TOOL:
            raise ConfigurationError(f"Unsupported tool: {tool_name}")
        request = _build_request(params)
        generate_request = _to_generate_request(request)
        backend = self._resolve_backend(generate_request)
        normalized = await backend.generate(generate_request)
        raise_if_empty_tool_response(
            has_tools=bool(request.tools),
            content=normalized.content,
            tool_calls=normalized.tool_calls,
        )
        return _build_generate_tool_response(
            normalized=normalized,
            model_name=request.model_name,
            provider=request.provider,
        )

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
        generate_request = _to_generate_request(request)
        backend = self._resolve_backend(generate_request)
        terminal_response: NormalizedLLMResponse | None = None
        async for event in backend.generate_stream(
            generate_request,
            should_stop=should_stop,
        ):
            if event.delta:
                yield LLMStreamEvent(delta=event.delta)
            if event.terminal_response is not None:
                terminal_response = event.terminal_response
        if terminal_response is None:
            raise ConfigurationError("Streaming backend completed without terminal response")
        raise_if_empty_tool_response(
            has_tools=bool(request.tools),
            content=terminal_response.content,
            tool_calls=terminal_response.tool_calls,
        )
        yield LLMStreamEvent(
            response=_build_generate_tool_response(
                normalized=terminal_response,
                model_name=request.model_name,
                provider=request.provider,
            )
        )

    def list_tools(self) -> list[str]:
        return [LLM_GENERATE_TOOL]

    def _resolve_backend(self, request: LLMGenerateRequest) -> AsyncLLMGenerateBackend:
        if self.default_backend is not None:
            return self.default_backend
        if self._force_native_backend:
            return self.native_backend
        selection = resolve_backend_selection(request)
        if selection.backend_key == "native_http":
            return self.native_backend
        return self.litellm_backend


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
    connection = _build_connection(credential)
    continuation_support = resolve_connection_continuation_support(
        connection.api_dialect,
        connection.interop_profile,
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
        reasoning_effort=_optional_reasoning_effort(model.get("reasoning_effort")),
        thinking_level=_optional_thinking_level(model.get("thinking_level")),
        thinking_budget=_optional_int(model.get("thinking_budget"), field_name="model.thinking_budget"),
        stop=_optional_string_list(model.get("stop")),
        tools=_optional_function_tool_list(params.get("tools")),
        continuation_items=_optional_record_list(params.get("continuation_items")),
        provider_continuation_state=_resolve_provider_continuation_state(
            params.get("provider_continuation_state"),
            continuation_support=continuation_support,
        ),
        continuation_support=continuation_support,
        connection=connection,
    )


def _serialize_tool_call(tool_call: Any) -> dict[str, Any]:
    payload = dict(tool_call.__dict__)
    if payload.get("arguments_error") is None:
        payload.pop("arguments_error", None)
    if payload.get("provider_payload") is None:
        payload.pop("provider_payload", None)
    return payload


def _build_generate_tool_response(
    *,
    normalized: NormalizedLLMResponse,
    model_name: str,
    provider: str | None,
) -> LLMGenerateToolResponse:
    return {
        "content": normalized.content,
        "finish_reason": normalized.finish_reason,
        "model_name": model_name,
        "provider": provider,
        "input_tokens": normalized.input_tokens,
        "output_tokens": normalized.output_tokens,
        "total_tokens": normalized.total_tokens,
        "tool_calls": [_serialize_tool_call(tool_call) for tool_call in normalized.tool_calls],
        "provider_response_id": normalized.provider_response_id,
        "output_items": normalized.provider_output_items,
    }


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
        reasoning_effort=request.reasoning_effort,
        thinking_level=request.thinking_level,
        thinking_budget=request.thinking_budget,
        stop=request.stop,
        tools=request.tools,
        continuation_items=request.continuation_items,
        provider_continuation_state=request.provider_continuation_state,
        force_tool_call=False,
    )


def _resolve_provider_continuation_state(
    raw_state: object,
    *,
    continuation_support: LLMContinuationSupport,
) -> dict[str, Any] | None:
    normalized_state = _optional_dict(raw_state)
    if normalized_state is None:
        return None
    if not allows_provider_continuation_state(continuation_support):
        return None
    return normalized_state


def _build_connection(credential: dict[str, Any]) -> LLMConnection:
    return LLMConnection(
        provider=_optional_string(credential.get("provider")),
        api_dialect=normalize_api_dialect(_optional_string(credential.get("api_dialect"))),
        api_key=_require_non_empty_string(credential.get("api_key"), "credential.api_key"),
        base_url=_optional_string(credential.get("base_url")),
        default_model=_optional_string(credential.get("default_model")),
        auth_strategy=normalize_auth_strategy(_optional_string(credential.get("auth_strategy"))),
        api_key_header_name=_optional_string(credential.get("api_key_header_name")),
        extra_headers=_optional_string_mapping(credential.get("extra_headers")),
        user_agent_override=_optional_string(credential.get("user_agent_override")),
        client_name=_optional_string(credential.get("client_name")),
        client_version=_optional_string(credential.get("client_version")),
        runtime_kind=normalize_runtime_kind(_optional_string(credential.get("runtime_kind"))),
        interop_profile=normalize_interop_profile(_optional_string(credential.get("interop_profile"))),
        context_window_tokens=_optional_int(
            credential.get("context_window_tokens"),
            field_name="credential.context_window_tokens",
        ),
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


def _optional_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field_name} must be an integer")
    return value


def _optional_reasoning_effort(value: Any) -> OpenAIReasoningEffort | None:
    normalized = _optional_string(value)
    if normalized is None:
        return None
    allowed: set[str] = {"none", "minimal", "low", "medium", "high", "xhigh"}
    if normalized not in allowed:
        raise ConfigurationError("model.reasoning_effort is invalid")
    return normalized  # type: ignore[return-value]


def _optional_thinking_level(value: Any) -> GeminiThinkingLevel | None:
    normalized = _optional_string(value)
    if normalized is None:
        return None
    allowed: set[str] = {"minimal", "low", "medium", "high"}
    if normalized not in allowed:
        raise ConfigurationError("model.thinking_level is invalid")
    return normalized  # type: ignore[return-value]


def _optional_function_tool_list(value: Any) -> list[LLMFunctionToolDefinition]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigurationError("tools must be an array")
    tools: list[LLMFunctionToolDefinition] = []
    for item in value:
        tool = _require_dict(item, "tools[]")
        tools.append(
            LLMFunctionToolDefinition(
                name=_require_non_empty_string(tool.get("name"), "tools[].name"),
                description=_require_non_empty_string(tool.get("description"), "tools[].description"),
                parameters=_require_dict(tool.get("parameters"), "tools[].parameters"),
                strict=_optional_bool(tool.get("strict"), default=True),
            )
        )
    return tools


def _optional_bool(value: Any, *, default: bool | None = None) -> bool:
    if value is None:
        if default is None:
            raise ConfigurationError("Expected bool value")
        return default
    if isinstance(value, bool):
        return value
    raise ConfigurationError("Expected bool value")


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError("Expected object value")
    return value


def _optional_record_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigurationError("continuation_items must be an array")
    normalized: list[dict[str, Any]] = []
    for item in value:
        normalized.append(_require_dict(item, "continuation_items[]"))
    return normalized


def _resolve_max_tokens(*, requested_value: Any, default_value: Any) -> int | None:
    requested_max_tokens = _optional_int(
        requested_value,
        field_name="model.max_tokens",
    )
    if requested_max_tokens is not None:
        return requested_max_tokens
    return _optional_int(
        default_value,
        field_name="credential.default_max_output_tokens",
    )


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
