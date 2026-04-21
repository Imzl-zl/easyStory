from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from typing import Any, Literal, NoReturn

import litellm

from ..errors import (
    ConfigurationError,
    UpstreamAuthenticationError,
    UpstreamRateLimitError,
    UpstreamServiceError,
    UpstreamTimeoutError,
)
from .interop.provider_interop_stream_support import StreamInterruptedError
from .interop.tool_name_codec import encode_tool_name
from .llm_backend import LLMBackendStreamEvent, StreamStopChecker
from .llm_endpoint_policy import normalize_custom_base_url
from .llm_error_support import (
    INCOMPLETE_STREAM_MESSAGE,
    build_responses_failed_message,
    looks_like_openai_chat_payload,
)
from .llm_interop_profiles import resolve_interop_capabilities
from .llm_protocol_requests import (
    _build_openai_chat_messages,
    _compile_tool_parameters,
    _resolve_openai_chat_max_tokens_field,
    prepare_generation_request,
)
from .llm_protocol_responses import parse_generation_response
from .llm_protocol_types import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    JSON_OBJECT_RESPONSE_FORMAT,
    LLMGenerateRequest,
    NormalizedLLMResponse,
    OPENAI_RESPONSES_TERMINAL_EVENT_NAMES,
)
from .llm_response_validation import raise_if_truncated_response
from .llm_stream_events import (
    build_truncated_stream_message,
    extract_stream_truncation_reason,
    parse_raw_stream_event,
    synthesize_stream_terminal_response,
)
from .llm_terminal_assembly import build_stream_completion


@dataclass(frozen=True)
class LiteLLMCallSpec:
    call_kind: Literal["completion", "responses"]
    output_api_dialect: Literal["openai_chat_completions", "openai_responses"]
    call_kwargs: dict[str, Any]
    tool_name_aliases: dict[str, str]


class LiteLLMBackend:
    async def generate(self, request: LLMGenerateRequest) -> NormalizedLLMResponse:
        call_spec = build_litellm_call_spec(request)
        try:
            response = await _execute_litellm_call(
                call_kind=call_spec.call_kind,
                call_kwargs=call_spec.call_kwargs,
            )
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            _raise_litellm_request_error(exc, streaming=False)
        payload = _model_dump_payload(response)
        output_api_dialect = _resolve_output_api_dialect(call_spec, payload)
        normalized = parse_generation_response(
            output_api_dialect,
            payload,
            tool_name_aliases=call_spec.tool_name_aliases,
        )
        raise_if_truncated_response(
            api_dialect=output_api_dialect,
            payload=payload,
            response_format=request.response_format,
            content=normalized.content,
        )
        return normalized

    async def generate_stream(
        self,
        request: LLMGenerateRequest,
        *,
        should_stop: StreamStopChecker | None = None,
    ) -> AsyncIterator[LLMBackendStreamEvent]:
        call_spec = build_litellm_call_spec(request)
        stream_kwargs = dict(call_spec.call_kwargs)
        stream_kwargs["stream"] = True
        try:
            stream = await _execute_litellm_call(
                call_kind=call_spec.call_kind,
                call_kwargs=stream_kwargs,
            )
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            _raise_litellm_request_error(exc, streaming=True)
        text_parts: list[str] = []
        raw_event_tuples: list[tuple[str | None, dict[str, Any]]] = []
        truncation_reason: str | None = None
        saw_terminal_event = False
        terminal_response: NormalizedLLMResponse | None = None
        stream_api_dialect = call_spec.output_api_dialect
        try:
            async for chunk in stream:
                if should_stop is not None and await should_stop():
                    await _raise_stream_interrupted(stream)
                payload = _model_dump_payload(chunk)
                event_name = _resolve_event_name(
                    call_kind=call_spec.call_kind,
                    payload=payload,
                )
                stream_api_dialect = _resolve_stream_api_dialect(
                    call_spec=call_spec,
                    payload=payload,
                    event_name=event_name,
                    current_api_dialect=stream_api_dialect,
                )
                if event_name == "response.failed":
                    raise ConfigurationError(build_responses_failed_message(payload))
                parsed = parse_raw_stream_event(
                    stream_api_dialect,
                    event_name=event_name,
                    payload=payload,
                    tool_name_aliases=call_spec.tool_name_aliases,
                )
                raw_event_tuples.append((parsed.event_name, payload))
                if truncation_reason is None:
                    truncation_reason = extract_stream_truncation_reason(parsed.stop_reason)
                if not saw_terminal_event:
                    saw_terminal_event = _is_terminal_stream_event(
                        api_dialect=stream_api_dialect,
                        event_name=parsed.event_name,
                        stop_reason=parsed.stop_reason,
                    )
                if parsed.terminal_response is not None:
                    terminal_response = parsed.terminal_response
                if not parsed.delta:
                    continue
                text_parts.append(parsed.delta)
                yield LLMBackendStreamEvent(
                    delta=parsed.delta,
                    stop_reason=parsed.stop_reason,
                )
        except StreamInterruptedError:
            raise
        except ConfigurationError:
            raise
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            _raise_litellm_request_error(exc, streaming=True)
        synthesized_terminal = synthesize_stream_terminal_response(
            stream_api_dialect,
            raw_events=raw_event_tuples,
            tool_name_aliases=call_spec.tool_name_aliases,
        )
        if synthesized_terminal is not None:
            terminal_response = synthesized_terminal
        normalized = build_stream_completion(
            api_dialect=stream_api_dialect,
            text_parts=text_parts,
            terminal_response=terminal_response,
        )
        if normalized is None:
            raise ConfigurationError("模型没有返回可展示的内容，请稍后重试。")
        if truncation_reason is not None:
            raise ConfigurationError(build_truncated_stream_message(truncation_reason))
        if not saw_terminal_event:
            raise ConfigurationError(INCOMPLETE_STREAM_MESSAGE)
        yield LLMBackendStreamEvent(terminal_response=normalized)


def build_litellm_call_spec(request: LLMGenerateRequest) -> LiteLLMCallSpec:
    prepared_request = prepare_generation_request(request)
    capabilities = resolve_interop_capabilities(
        request.connection.api_dialect,
        request.connection.interop_profile,
    )
    tool_name_aliases = dict(prepared_request.tool_name_aliases)
    base_call_kwargs = _build_base_call_kwargs(request, prepared_request.headers)
    if request.connection.api_dialect == "openai_responses":
        return LiteLLMCallSpec(
            call_kind="responses",
            output_api_dialect="openai_responses",
            call_kwargs=_build_responses_call_kwargs(base_call_kwargs, prepared_request.json_body),
            tool_name_aliases=tool_name_aliases,
        )
    if request.connection.api_dialect == "openai_chat_completions":
        return LiteLLMCallSpec(
            call_kind="completion",
            output_api_dialect="openai_chat_completions",
            call_kwargs=_build_openai_chat_call_kwargs(
                base_call_kwargs, prepared_request.json_body
            ),
            tool_name_aliases=tool_name_aliases,
        )
    return LiteLLMCallSpec(
        call_kind="completion",
        output_api_dialect="openai_chat_completions",
        call_kwargs=_build_openai_compatible_call_kwargs(
            request=request,
            base_call_kwargs=base_call_kwargs,
            tool_name_aliases=tool_name_aliases,
            capabilities=capabilities,
        ),
        tool_name_aliases=tool_name_aliases,
    )


def preview_litellm_call_spec(request: LLMGenerateRequest) -> dict[str, Any]:
    return asdict(build_litellm_call_spec(request))


def _build_base_call_kwargs(
    request: LLMGenerateRequest,
    prepared_headers: dict[str, str],
) -> dict[str, Any]:
    call_kwargs: dict[str, Any] = {
        "model": _resolve_litellm_model_name(request),
        "api_key": request.connection.api_key,
        "timeout": DEFAULT_REQUEST_TIMEOUT_SECONDS,
    }
    api_base = _normalize_litellm_api_base(request)
    if api_base is not None and not _is_official_openai_api_base(request, api_base):
        call_kwargs["api_base"] = api_base
    extra_headers = _build_litellm_extra_headers(request, prepared_headers)
    if extra_headers:
        call_kwargs["extra_headers"] = extra_headers
    if _uses_openai_compatible_routing(request):
        call_kwargs["custom_llm_provider"] = "openai"
    return call_kwargs


def _build_responses_call_kwargs(
    base_call_kwargs: dict[str, Any],
    prepared_json_body: dict[str, Any],
) -> dict[str, Any]:
    call_kwargs = dict(base_call_kwargs)
    body = dict(prepared_json_body)
    body.pop("model", None)
    body.pop("stop", None)
    call_kwargs.update(body)
    return call_kwargs


def _build_openai_chat_call_kwargs(
    base_call_kwargs: dict[str, Any],
    prepared_json_body: dict[str, Any],
) -> dict[str, Any]:
    call_kwargs = dict(base_call_kwargs)
    body = dict(prepared_json_body)
    body.pop("model", None)
    call_kwargs.update(body)
    return call_kwargs


def _build_openai_compatible_call_kwargs(
    *,
    request: LLMGenerateRequest,
    base_call_kwargs: dict[str, Any],
    tool_name_aliases: dict[str, str],
    capabilities: Any,
) -> dict[str, Any]:
    call_kwargs = dict(base_call_kwargs)
    call_kwargs["messages"] = _build_openai_chat_messages(
        request,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=capabilities.tool_name_policy,
    )
    if request.temperature is not None:
        call_kwargs["temperature"] = request.temperature
    if request.max_tokens is not None:
        call_kwargs[_resolve_openai_chat_max_tokens_field(request.connection)] = request.max_tokens
    if request.top_p is not None:
        call_kwargs["top_p"] = request.top_p
    if request.stop:
        call_kwargs["stop"] = list(request.stop)
    if request.reasoning_effort is not None:
        call_kwargs["reasoning_effort"] = request.reasoning_effort
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        call_kwargs["response_format"] = {"type": "json_object"}
    if request.tools:
        call_kwargs["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": encode_tool_name(
                        tool.name,
                        tool_name_aliases=tool_name_aliases,
                        policy=capabilities.tool_name_policy,
                    ),
                    "description": tool.description,
                    "parameters": _compile_tool_parameters(
                        tool.parameters,
                        capabilities=capabilities,
                    ),
                    "strict": tool.strict,
                },
            }
            for tool in request.tools
        ]
        if capabilities.supports_parallel_tool_calls:
            call_kwargs["parallel_tool_calls"] = True
        if request.force_tool_call:
            call_kwargs["tool_choice"] = "required"
    return call_kwargs


def _resolve_litellm_model_name(request: LLMGenerateRequest) -> str:
    model_name = request.model_name.strip()
    if request.connection.api_dialect in {"openai_chat_completions", "openai_responses"}:
        if _uses_openai_compatible_routing(request):
            if model_name.startswith("openai/"):
                return model_name
            return f"openai/{model_name}"
        return model_name
    if "/" in model_name:
        return model_name
    if request.connection.api_dialect == "anthropic_messages":
        return f"anthropic/{model_name}"
    if request.connection.api_dialect == "gemini_generate_content":
        return f"gemini/{model_name}"
    raise ConfigurationError(
        f"Unsupported api_dialect for LiteLLM backend: {request.connection.api_dialect}"
    )


def _uses_openai_compatible_routing(request: LLMGenerateRequest) -> bool:
    if request.connection.api_dialect not in {"openai_chat_completions", "openai_responses"}:
        return False
    base_url = normalize_custom_base_url(request.connection.base_url)
    if base_url is None:
        return False
    return request.connection.provider not in {None, "openai"} or "api.openai.com" not in base_url


def _is_official_openai_api_base(request: LLMGenerateRequest, api_base: str) -> bool:
    if request.connection.api_dialect not in {"openai_chat_completions", "openai_responses"}:
        return False
    if request.connection.provider not in {None, "openai"}:
        return False
    return "api.openai.com" in api_base


def _build_litellm_extra_headers(
    request: LLMGenerateRequest,
    prepared_headers: dict[str, str],
) -> dict[str, str] | None:
    auth_header_names = {"authorization", "x-api-key", "x-goog-api-key"}
    if request.connection.api_key_header_name is not None:
        auth_header_names.add(request.connection.api_key_header_name.lower())
    headers = {
        key: value
        for key, value in prepared_headers.items()
        if key.lower() not in auth_header_names and key.lower() != "content-type"
    }
    return headers or None


def _normalize_litellm_api_base(request: LLMGenerateRequest) -> str | None:
    api_base = normalize_custom_base_url(request.connection.base_url)
    if api_base is None:
        return None
    if request.connection.api_dialect != "gemini_generate_content":
        return api_base
    if "/v1beta/models" in api_base or "/v1/models" in api_base:
        return api_base
    return f"{api_base.rstrip('/')}/v1beta/models"


def _resolve_event_name(*, call_kind: str, payload: dict[str, Any]) -> str | None:
    if call_kind == "responses":
        event_type = payload.get("type")
        if isinstance(event_type, str) and event_type.strip():
            return event_type
    return None


def _resolve_output_api_dialect(
    call_spec: LiteLLMCallSpec,
    payload: dict[str, Any],
) -> Literal["openai_chat_completions", "openai_responses"]:
    if call_spec.call_kind == "responses" and looks_like_openai_chat_payload(payload):
        return "openai_chat_completions"
    return call_spec.output_api_dialect


def _resolve_stream_api_dialect(
    *,
    call_spec: LiteLLMCallSpec,
    payload: dict[str, Any],
    event_name: str | None,
    current_api_dialect: Literal["openai_chat_completions", "openai_responses"],
) -> Literal["openai_chat_completions", "openai_responses"]:
    if current_api_dialect == "openai_chat_completions":
        return current_api_dialect
    if call_spec.call_kind != "responses":
        return current_api_dialect
    if event_name is not None:
        return current_api_dialect
    if looks_like_openai_chat_payload(payload):
        return "openai_chat_completions"
    return current_api_dialect


def _is_terminal_stream_event(
    *, api_dialect: str, event_name: str | None, stop_reason: str | None
) -> bool:
    if api_dialect == "openai_chat_completions":
        return stop_reason is not None
    if api_dialect == "openai_responses":
        return event_name in OPENAI_RESPONSES_TERMINAL_EVENT_NAMES
    raise ConfigurationError(f"Unsupported LiteLLM stream dialect: {api_dialect}")


def _model_dump_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        payload = model_dump(exclude_none=True, by_alias=True)
        if isinstance(payload, dict):
            return payload
    raise ConfigurationError("LiteLLM returned an unsupported payload object")


async def _execute_litellm_call(
    *,
    call_kind: Literal["completion", "responses"],
    call_kwargs: dict[str, Any],
) -> Any:
    if call_kind == "responses":
        return await litellm.aresponses(**call_kwargs)
    if call_kind == "completion":
        return await litellm.acompletion(**call_kwargs)
    raise ConfigurationError(f"Unsupported LiteLLM call kind: {call_kind}")


def _raise_litellm_request_error(error: Exception, *, streaming: bool) -> NoReturn:
    message = _format_litellm_error(error, streaming=streaming)
    if isinstance(error, litellm.AuthenticationError):
        raise UpstreamAuthenticationError(message) from error
    if isinstance(error, litellm.RateLimitError):
        raise UpstreamRateLimitError(message) from error
    if isinstance(error, litellm.Timeout):
        raise UpstreamTimeoutError(message) from error
    if isinstance(
        error,
        (
            litellm.APIConnectionError,
            litellm.ServiceUnavailableError,
            litellm.InternalServerError,
        ),
    ):
        raise UpstreamServiceError(message) from error
    if isinstance(
        error,
        (
            litellm.BadRequestError,
            litellm.NotFoundError,
            litellm.ContentPolicyViolationError,
        ),
    ):
        raise ConfigurationError(message) from error
    if isinstance(error, litellm.APIError):
        raise UpstreamServiceError(message) from error
    raise ConfigurationError(message) from error


def _format_litellm_error(error: Exception, *, streaming: bool) -> str:
    status_code = getattr(error, "status_code", None)
    message = getattr(error, "message", None)
    detail = message if isinstance(message, str) and message.strip() else str(error).strip()
    prefix = "LLM streaming request failed" if streaming else "LLM request failed"
    if isinstance(status_code, int):
        if detail:
            return f"{prefix}: HTTP {status_code} - {detail}"
        return f"{prefix}: HTTP {status_code}"
    if detail:
        return f"{prefix}: {detail}"
    return prefix


async def _aclose_stream(stream: Any) -> None:
    aclose = getattr(stream, "aclose", None)
    if callable(aclose):
        await aclose()


async def _raise_stream_interrupted(stream: Any) -> NoReturn:
    interruption = StreamInterruptedError("Client disconnected during streaming")
    try:
        await _aclose_stream(stream)
    except Exception as exc:
        raise interruption from exc
    raise interruption
