from __future__ import annotations

import json
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


@dataclass
class StreamEventBuffer:
    event_name: str | None
    data_lines: list[str]


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
) -> NormalizedLLMResponse:
    buffer = StreamEventBuffer(event_name=None, data_lines=[])
    text_parts: list[str] = []
    raw_events: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS) as client:
        async with client.stream(
            request.method,
            request.url,
            headers=request.headers,
            json=request.json_body,
        ) as response:
            print(f"HTTP {response.status_code}")
            if response.status_code >= 400:
                body = await response.aread()
                raise ConfigurationError(
                    f"Probe failed with HTTP {response.status_code}: "
                    f"{body.decode('utf-8', errors='replace')}"
                )
            async for line in response.aiter_lines():
                _consume_stream_line(
                    line,
                    buffer=buffer,
                    api_dialect=api_dialect,
                    text_parts=text_parts,
                    raw_events=raw_events,
                )
    _flush_stream_event(
        buffer,
        api_dialect=api_dialect,
        text_parts=text_parts,
        raw_events=raw_events,
    )
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


def _consume_stream_line(
    line: str,
    *,
    buffer: StreamEventBuffer,
    api_dialect: str,
    text_parts: list[str],
    raw_events: list[dict[str, Any]],
) -> None:
    if line.startswith("event:"):
        buffer.event_name = line.partition(":")[2].strip() or None
        return
    if line.startswith("data:"):
        buffer.data_lines.append(line.partition(":")[2].lstrip())
        return
    if line != "":
        return
    _flush_stream_event(
        buffer,
        api_dialect=api_dialect,
        text_parts=text_parts,
        raw_events=raw_events,
    )


def _flush_stream_event(
    buffer: StreamEventBuffer,
    *,
    api_dialect: str,
    text_parts: list[str],
    raw_events: list[dict[str, Any]],
) -> None:
    if not buffer.data_lines:
        buffer.event_name = None
        return
    raw_data = "\n".join(buffer.data_lines).strip()
    buffer.data_lines.clear()
    if not raw_data or raw_data == STREAM_DONE_MARKER:
        buffer.event_name = None
        return
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Streaming probe returned non-JSON SSE payload") from exc
    raw_events.append({"event": buffer.event_name, "data": payload})
    delta = _extract_stream_delta(api_dialect, buffer.event_name, payload)
    if delta:
        text_parts.append(delta)
    buffer.event_name = None


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


def _extract_openai_responses_delta(
    event_name: str | None,
    payload: dict[str, Any],
) -> str:
    if event_name == "response.output_text.delta" and isinstance(payload.get("delta"), str):
        return payload["delta"]
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        parts.extend(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
    return "".join(parts)


def _extract_anthropic_delta(payload: dict[str, Any]) -> str:
    delta = payload.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("text"), str):
        return delta["text"]
    return ""


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


def _build_gemini_stream_url(url: str) -> str:
    if ":streamGenerateContent" in url:
        return url
    separator = "&" if "?" in url else "?"
    return url.replace(":generateContent", ":streamGenerateContent") + f"{separator}alt=sse"
