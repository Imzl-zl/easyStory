from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import httpx

from ..errors import ConfigurationError
from .llm_protocol_types import DEFAULT_REQUEST_TIMEOUT_SECONDS, PreparedLLMHttpRequest

STREAM_DONE_MARKER = "[DONE]"
STREAM_STOP_CHECK_INTERVAL_SECONDS = 0.25
StreamStopChecker = Callable[[], Awaitable[bool]]


@dataclass
class StreamEventBuffer:
    event_name: str | None
    data_lines: list[str]


@dataclass(frozen=True)
class RawStreamEvent:
    event_name: str | None
    payload: dict[str, Any]


class StreamInterruptedError(ConfigurationError):
    """Raised when the client disconnects during streaming."""


async def iterate_raw_stream_events(
    request: PreparedLLMHttpRequest,
    *,
    print_status: bool = False,
    should_stop: StreamStopChecker | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> AsyncIterator[RawStreamEvent]:
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
            async for raw_event in _iterate_response_events(
                response,
                buffer=buffer,
                should_stop=should_stop,
            ):
                yield raw_event
    flushed = flush_raw_stream_event(buffer)
    if flushed is not None:
        yield flushed


async def _iterate_response_events(
    response: Any,
    *,
    buffer: StreamEventBuffer,
    should_stop: StreamStopChecker | None,
) -> AsyncIterator[RawStreamEvent]:
    line_iterator = response.aiter_lines().__aiter__()
    pending_line_task: asyncio.Task[str] | None = None
    try:
        while True:
            if pending_line_task is None:
                pending_line_task = asyncio.create_task(anext(line_iterator))
            if await _should_interrupt_stream(should_stop):
                await _cancel_pending_line_task(pending_line_task)
                raise StreamInterruptedError("Client disconnected during streaming")
            try:
                line = await asyncio.wait_for(
                    asyncio.shield(pending_line_task),
                    timeout=STREAM_STOP_CHECK_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                continue
            except StopAsyncIteration:
                pending_line_task = None
                break
            pending_line_task = None
            for raw_event in consume_raw_stream_line(line, buffer=buffer):
                yield raw_event
    finally:
        if pending_line_task is not None:
            await _cancel_pending_line_task(pending_line_task)


def consume_raw_stream_line(
    line: str,
    *,
    buffer: StreamEventBuffer,
) -> list[RawStreamEvent]:
    if line.startswith("event:"):
        buffer.event_name = line.partition(":")[2].strip() or None
        return []
    if line.startswith("data:"):
        buffer.data_lines.append(line.partition(":")[2].lstrip())
        return []
    if line != "":
        return []
    raw_event = flush_raw_stream_event(buffer)
    if raw_event is None:
        return []
    return [raw_event]


def flush_raw_stream_event(buffer: StreamEventBuffer) -> RawStreamEvent | None:
    if not buffer.data_lines:
        buffer.event_name = None
        return None
    raw_data = "\n".join(buffer.data_lines).strip()
    event_name = buffer.event_name
    buffer.data_lines.clear()
    buffer.event_name = None
    if not raw_data or raw_data == STREAM_DONE_MARKER:
        return None
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Streaming probe returned non-JSON SSE payload") from exc
    return RawStreamEvent(event_name=event_name, payload=payload)


async def _cancel_pending_line_task(task: asyncio.Task[str]) -> None:
    if not task.done():
        task.cancel()
    with suppress(asyncio.CancelledError, StopAsyncIteration):
        await task


async def _should_interrupt_stream(should_stop: StreamStopChecker | None) -> bool:
    if should_stop is None:
        return False
    return await should_stop()


def _build_stream_http_error_message(status_code: int, response_text: str) -> str:
    suffix = response_text.strip()
    if suffix:
        return f"LLM streaming request failed: HTTP {status_code} - {suffix}"
    return f"LLM streaming request failed: HTTP {status_code}"
