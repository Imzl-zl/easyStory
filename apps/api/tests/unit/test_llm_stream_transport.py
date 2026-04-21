from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm import llm_stream_transport as transport_module
from app.shared.runtime.llm.llm_protocol_types import PreparedLLMHttpRequest
from app.shared.runtime.llm.llm_stream_transport import (
    StreamEventBuffer,
    StreamInterruptedError,
    consume_raw_stream_line,
    flush_raw_stream_event,
    iterate_raw_stream_events,
)


def test_consume_raw_stream_line_emits_event_after_blank_separator() -> None:
    buffer = StreamEventBuffer(event_name=None, data_lines=[])

    assert consume_raw_stream_line("event: response.output_text.delta", buffer=buffer) == []
    assert consume_raw_stream_line('data: {"delta":"你好"}', buffer=buffer) == []

    events = consume_raw_stream_line("", buffer=buffer)

    assert len(events) == 1
    assert events[0].event_name == "response.output_text.delta"
    assert events[0].payload == {"delta": "你好"}


def test_flush_raw_stream_event_rejects_non_json_payload() -> None:
    buffer = StreamEventBuffer(event_name=None, data_lines=["not-json"])

    with pytest.raises(ConfigurationError, match="non-JSON SSE payload"):
        flush_raw_stream_event(buffer)


@pytest.mark.asyncio
async def test_iterate_raw_stream_events_interrupts_pending_line_read(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-test", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            await asyncio.sleep(transport_module.STREAM_STOP_CHECK_INTERVAL_SECONDS * 2)
            yield 'data: {"delta":"too-late"}'
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(transport_module.httpx, "AsyncClient", FakeClient)

    async def should_stop() -> bool:
        return True

    with pytest.raises(StreamInterruptedError, match="Client disconnected during streaming"):
        async for _event in iterate_raw_stream_events(
            request,
            should_stop=should_stop,
        ):
            pass
