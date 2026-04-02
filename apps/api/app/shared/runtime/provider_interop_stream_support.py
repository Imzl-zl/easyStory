from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .errors import ConfigurationError
from .llm_protocol import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
)

STREAM_DONE_MARKER = "[DONE]"
STREAM_STOP_CHECK_INTERVAL_SECONDS = 0.25

StreamStopChecker = Callable[[], Awaitable[bool]]


@dataclass
class StreamEventBuffer:
    event_name: str | None
    data_lines: list[str]


@dataclass(frozen=True)
class ParsedStreamEvent:
    event_name: str | None
    payload: dict[str, Any]
    delta: str
    stop_reason: str | None = None


class StreamInterruptedError(ConfigurationError):
    """Raised when the client disconnects during streaming."""


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
        )
    json_body["stream"] = True
    return PreparedLLMHttpRequest(
        method=request.method,
        url=request.url,
        headers=headers,
        json_body=json_body,
    )


async def execute_stream_probe_request(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
    print_response: bool,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> NormalizedLLMResponse:
    text_parts: list[str] = []
    raw_events: list[dict[str, Any]] = []
    async for event in iterate_stream_request(
        request,
        api_dialect=api_dialect,
        print_status=True,
        timeout_seconds=timeout_seconds,
    ):
        raw_events.append({"event": event.event_name, "data": event.payload})
        if event.delta:
            text_parts.append(event.delta)
    content = "".join(text_parts).strip()
    if print_response:
        print(
            json.dumps(
                {"events": raw_events, "content": content},
                ensure_ascii=False,
                indent=2,
            )
        )
    if not content:
        raise ConfigurationError("Streaming probe returned no text content")
    return NormalizedLLMResponse(
        content=content,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
    )


async def iterate_stream_request(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
    print_status: bool = False,
    should_stop: StreamStopChecker | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> AsyncIterator[ParsedStreamEvent]:
    buffer = StreamEventBuffer(event_name=None, data_lines=[])
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        async with client.stream(
            request.method,
            request.url,
            headers=request.headers,
            json=request.json_body,
        ) as response:
            if print_status:
                print(f"HTTP {response.status_code}")
            if response.status_code >= 400:
                body = await response.aread()
                raise ConfigurationError(
                    _build_stream_http_error_message(
                        response.status_code,
                        body.decode("utf-8", errors="replace"),
                    )
                )
            line_iterator = response.aiter_lines().__aiter__()
            while True:
                if await _should_interrupt_stream(should_stop):
                    raise StreamInterruptedError("Client disconnected during streaming")
                try:
                    line = await asyncio.wait_for(
                        anext(line_iterator),
                        timeout=STREAM_STOP_CHECK_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    continue
                except StopAsyncIteration:
                    break
                for event in _consume_stream_line(
                    line,
                    buffer=buffer,
                    api_dialect=api_dialect,
                ):
                    yield event
    for event in _flush_stream_event(buffer, api_dialect=api_dialect):
        yield event


def _consume_stream_line(
    line: str,
    *,
    buffer: StreamEventBuffer,
    api_dialect: str,
 ) -> list[ParsedStreamEvent]:
    if line.startswith("event:"):
        buffer.event_name = line.partition(":")[2].strip() or None
        return []
    if line.startswith("data:"):
        buffer.data_lines.append(line.partition(":")[2].lstrip())
        return []
    if line != "":
        return []
    return _flush_stream_event(buffer, api_dialect=api_dialect)


def _flush_stream_event(
    buffer: StreamEventBuffer,
    *,
    api_dialect: str,
 ) -> list[ParsedStreamEvent]:
    if not buffer.data_lines:
        buffer.event_name = None
        return []
    raw_data = "\n".join(buffer.data_lines).strip()
    buffer.data_lines.clear()
    if not raw_data or raw_data == STREAM_DONE_MARKER:
        buffer.event_name = None
        return []
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Streaming probe returned non-JSON SSE payload") from exc
    delta = _extract_stream_delta(api_dialect, buffer.event_name, payload)
    event = ParsedStreamEvent(
        event_name=buffer.event_name,
        payload=payload,
        delta=delta,
        stop_reason=_extract_stream_stop_reason(api_dialect, buffer.event_name, payload),
    )
    buffer.event_name = None
    return [event]


def _extract_stream_delta(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
) -> str:
    if api_dialect == "openai_chat_completions":
        return _extract_openai_chat_delta(payload)
    if api_dialect == "openai_responses":
        return _extract_openai_responses_delta(event_name, payload)
    if api_dialect == "anthropic_messages":
        return _extract_anthropic_delta(payload)
    return _extract_gemini_delta(payload)


def extract_stream_truncation_reason(stop_reason: str | None) -> str | None:
    if stop_reason is None:
        return None
    normalized = stop_reason.strip()
    if not normalized:
        return None
    if normalized.lower() in {"length", "max_tokens", "max_output_tokens"}:
        return normalized
    if normalized.upper() == "MAX_TOKENS":
        return normalized
    return None


def build_truncated_stream_message(stop_reason: str) -> str:
    return (
        "上游在输出尚未完成时提前停止了这次回复，"
        f"当前只收到部分内容（stop_reason={stop_reason}）。"
        "请缩短问题、关闭流式，或切换更稳定的连接后重试。"
    )


def _extract_stream_stop_reason(
    api_dialect: str,
    event_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    if api_dialect == "openai_chat_completions":
        return _extract_openai_chat_stop_reason(payload)
    if api_dialect == "openai_responses":
        return _extract_openai_responses_stop_reason(event_name, payload)
    if api_dialect == "anthropic_messages":
        return _extract_anthropic_stop_reason(payload)
    return _extract_gemini_stop_reason(payload)


def _extract_openai_chat_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )


def _extract_openai_chat_stop_reason(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _extract_openai_responses_delta(
    event_name: str | None,
    payload: dict[str, Any],
) -> str:
    if event_name == "response.output_text.delta" and isinstance(payload.get("delta"), str):
        return payload["delta"]
    return ""


def _extract_openai_responses_stop_reason(
    event_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    if event_name != "response.completed":
        return None
    incomplete_details = payload.get("incomplete_details")
    if isinstance(incomplete_details, dict):
        reason = incomplete_details.get("reason")
        if isinstance(reason, str):
            return reason
    response = payload.get("response")
    if isinstance(response, dict):
        incomplete_details = response.get("incomplete_details")
        if isinstance(incomplete_details, dict):
            reason = incomplete_details.get("reason")
            if isinstance(reason, str):
                return reason
    return None


def _extract_anthropic_delta(payload: dict[str, Any]) -> str:
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("text"), str):
        return delta["text"]
    return ""


def _extract_anthropic_stop_reason(payload: dict[str, Any]) -> str | None:
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("stop_reason"), str):
        return delta["stop_reason"]
    stop_reason = payload.get("stop_reason")
    return stop_reason if isinstance(stop_reason, str) else None


def _extract_gemini_delta(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return ""
    content = candidate.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    return "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def _extract_gemini_stop_reason(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return None
    finish_reason = candidate.get("finishReason")
    return finish_reason if isinstance(finish_reason, str) else None


def _build_gemini_stream_url(url: str) -> str:
    if ":streamGenerateContent" in url:
        return url
    separator = "&" if "?" in url else "?"
    return url.replace(":generateContent", ":streamGenerateContent") + f"{separator}alt=sse"


async def _should_interrupt_stream(should_stop: StreamStopChecker | None) -> bool:
    if should_stop is None:
        return False
    return await should_stop()


def _build_stream_http_error_message(status_code: int, response_text: str) -> str:
    suffix = response_text.strip()
    if suffix:
        return f"LLM streaming request failed: HTTP {status_code} - {suffix}"
    return f"LLM streaming request failed: HTTP {status_code}"
