from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ...errors import ConfigurationError
from ..llm_protocol import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
)
from ..llm_stream_events import (
    ParsedStreamEvent,
    build_truncated_stream_message,
    extract_stream_truncation_reason,
    parse_raw_stream_event,
)
from ..llm_stream_transport import (
    StreamEventBuffer,
    StreamInterruptedError,
    STREAM_STOP_CHECK_INTERVAL_SECONDS,
    StreamStopChecker,
    consume_raw_stream_line,
    flush_raw_stream_event,
    iterate_raw_stream_events,
)
from ..llm_terminal_assembly import build_stream_completion

__all__ = [
    "ParsedStreamEvent",
    "STREAM_STOP_CHECK_INTERVAL_SECONDS",
    "StreamEventBuffer",
    "StreamInterruptedError",
    "StreamStopChecker",
    "build_stream_completion",
    "build_stream_probe_request",
    "build_truncated_stream_message",
    "execute_stream_probe_request",
    "extract_stream_truncation_reason",
    "httpx",
    "iterate_stream_request",
]


def build_stream_probe_request(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
) -> PreparedLLMHttpRequest:
    json_body = dict(request.json_body)
    headers = dict(request.headers)
    headers["Accept"] = "text/event-stream"
    if api_dialect == "gemini_generate_content":
        return PreparedLLMHttpRequest(
            method=request.method,
            url=_build_gemini_stream_url(request.url),
            headers=headers,
            json_body=json_body,
            interop_profile=request.interop_profile,
        )
    json_body["stream"] = True
    return PreparedLLMHttpRequest(
        method=request.method,
        url=request.url,
        headers=headers,
        json_body=json_body,
        interop_profile=request.interop_profile,
    )


async def execute_stream_probe_request(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
    print_response: bool,
    interop_profile: str | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> NormalizedLLMResponse:
    active_interop_profile = interop_profile or request.interop_profile
    text_parts: list[str] = []
    raw_events: list[dict[str, Any]] = []
    terminal_response: NormalizedLLMResponse | None = None
    async for event in iterate_stream_request(
        request,
        api_dialect=api_dialect,
        interop_profile=active_interop_profile,
        print_status=True,
        timeout_seconds=timeout_seconds,
    ):
        raw_events.append({"event": event.event_name, "data": event.payload})
        if event.terminal_response is not None:
            terminal_response = event.terminal_response
        if event.delta:
            text_parts.append(event.delta)
    normalized = build_stream_completion(
        api_dialect=api_dialect,
        text_parts=text_parts,
        terminal_response=terminal_response,
    )
    if print_response:
        print(
            json.dumps(
                {
                    "events": raw_events,
                    "content": normalized.content if normalized is not None else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    if normalized is None:
        raise ConfigurationError("Streaming probe returned no text content")
    return normalized


async def iterate_stream_request(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
    interop_profile: str | None = None,
    print_status: bool = False,
    should_stop: StreamStopChecker | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> AsyncIterator[ParsedStreamEvent]:
    active_interop_profile = interop_profile or request.interop_profile
    async for raw_event in iterate_raw_stream_events(
        request,
        print_status=print_status,
        should_stop=should_stop,
        timeout_seconds=timeout_seconds,
    ):
        yield parse_raw_stream_event(
            api_dialect,
            event_name=raw_event.event_name,
            payload=raw_event.payload,
            interop_profile=active_interop_profile,
        )


def _consume_stream_line(
    line: str,
    *,
    buffer: StreamEventBuffer,
    api_dialect: str,
    interop_profile: str | None = None,
) -> list[ParsedStreamEvent]:
    return [
        parse_raw_stream_event(
            api_dialect,
            event_name=raw_event.event_name,
            payload=raw_event.payload,
            interop_profile=interop_profile,
        )
        for raw_event in consume_raw_stream_line(line, buffer=buffer)
    ]


def _flush_stream_event(
    buffer: StreamEventBuffer,
    *,
    api_dialect: str,
    interop_profile: str | None = None,
) -> list[ParsedStreamEvent]:
    raw_event = flush_raw_stream_event(buffer)
    if raw_event is None:
        return []
    return [
        parse_raw_stream_event(
            api_dialect,
            event_name=raw_event.event_name,
            payload=raw_event.payload,
            interop_profile=interop_profile,
        )
    ]


def _build_gemini_stream_url(url: str) -> str:
    if ":streamGenerateContent" in url:
        return url
    separator = "&" if "?" in url else "?"
    return url.replace(":generateContent", ":streamGenerateContent") + f"{separator}alt=sse"
