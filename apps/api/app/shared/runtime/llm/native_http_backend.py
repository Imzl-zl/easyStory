from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from ..errors import ConfigurationError
from .interop import provider_interop_stream_support as stream_support
from .llm_backend import LLMBackendStreamEvent, StreamStopChecker
from .llm_error_support import INCOMPLETE_STREAM_MESSAGE, build_responses_failed_message
from .llm_protocol_requests import prepare_generation_request
from .llm_protocol_responses import parse_generation_response
from .llm_protocol_types import (
    HttpJsonResponse,
    LLMGenerateRequest,
    NormalizedLLMResponse,
    OPENAI_RESPONSES_TERMINAL_EVENT_NAMES,
    send_json_http_request,
)
from .llm_response_validation import (
    build_truncated_response_message,
    raise_if_empty_tool_response,
    raise_if_truncated_response,
)
from .llm_stream_completion_support import (
    BackendStreamCompletionState,
    finalize_backend_stream_completion,
    record_backend_stream_event,
)
from .llm_protocol_responses import extract_response_truncation_reason


class AsyncLlmRequestSender(Protocol):
    async def __call__(self, request) -> HttpJsonResponse: ...


class NativeHttpLLMBackend:
    def __init__(
        self,
        *,
        request_sender: AsyncLlmRequestSender | None = None,
    ) -> None:
        self.request_sender = request_sender or _default_request_sender

    async def generate(self, request: LLMGenerateRequest) -> NormalizedLLMResponse:
        prepared_request = prepare_generation_request(request)
        response = await self.request_sender(prepared_request)
        if response.status_code >= 400:
            raise ConfigurationError(_build_http_error_message(response))
        payload = response.json_body or {}
        try:
            normalized = parse_generation_response(
                request.connection.api_dialect,
                payload,
                tool_name_aliases=prepared_request.tool_name_aliases,
            )
        except ConfigurationError as exc:
            truncation_reason = extract_response_truncation_reason(
                request.connection.api_dialect,
                payload,
            )
            if truncation_reason is not None:
                raise ConfigurationError(
                    build_truncated_response_message(truncation_reason)
                ) from exc
            raise
        raise_if_truncated_response(
            api_dialect=request.connection.api_dialect,
            payload=response.json_body or {},
            response_format=request.response_format,
            content=normalized.content,
        )
        raise_if_empty_tool_response(
            has_tools=bool(request.tools),
            content=normalized.content,
            tool_calls=normalized.tool_calls,
        )
        return normalized

    async def generate_stream(
        self,
        request: LLMGenerateRequest,
        *,
        should_stop: StreamStopChecker | None = None,
    ) -> AsyncIterator[LLMBackendStreamEvent]:
        api_dialect = request.connection.api_dialect
        prepared_request = stream_support.build_stream_probe_request(
            prepare_generation_request(request),
            api_dialect=api_dialect,
        )
        completion_state = BackendStreamCompletionState()
        async for event in stream_support.iterate_stream_request(
            prepared_request,
            api_dialect=api_dialect,
            should_stop=should_stop,
        ):
            if event.event_name == "response.failed":
                raise ConfigurationError(build_responses_failed_message(event.payload))
            delta = record_backend_stream_event(
                completion_state,
                recorded_event_name=event.event_name,
                raw_payload=event.payload,
                parsed_event=event,
                terminal_event_detected=_is_terminal_stream_event(
                    api_dialect=api_dialect,
                    event=event,
                ),
            )
            if delta is None:
                continue
            yield LLMBackendStreamEvent(
                delta=delta,
                stop_reason=event.stop_reason,
            )
        normalized = finalize_backend_stream_completion(
            completion_state,
            api_dialect=api_dialect,
            tool_name_aliases=prepared_request.tool_name_aliases,
            has_tools=bool(request.tools),
            incomplete_stream_message=INCOMPLETE_STREAM_MESSAGE,
        )
        yield LLMBackendStreamEvent(terminal_response=normalized)


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


def _is_terminal_stream_event(
    *,
    api_dialect: str,
    event: stream_support.ParsedStreamEvent,
) -> bool:
    if api_dialect == "openai_chat_completions":
        return event.stop_reason is not None
    if api_dialect == "openai_responses":
        return event.event_name in OPENAI_RESPONSES_TERMINAL_EVENT_NAMES
    if api_dialect == "anthropic_messages":
        return event.event_name == "message_stop" or event.stop_reason is not None
    if api_dialect == "gemini_generate_content":
        return event.stop_reason is not None
    raise ConfigurationError(
        f"Unsupported api_dialect for stream terminal detection: {api_dialect}"
    )


async def _default_request_sender(request) -> HttpJsonResponse:
    return await send_json_http_request(request)
