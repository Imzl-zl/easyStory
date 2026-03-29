from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.llm_protocol import PreparedLLMHttpRequest
from app.shared.runtime import provider_interop_stream_support as stream_support


def test_build_stream_probe_request_sets_stream_flag_for_openai_responses() -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Authorization": "Bearer test-key"},
        json_body={"model": "gpt-5.2-codex"},
    )

    streamed = stream_support.build_stream_probe_request(
        request,
        api_dialect="openai_responses",
    )

    assert streamed.url == "https://proxy.example.com/v1/responses"
    assert streamed.headers["Accept"] == "text/event-stream"
    assert streamed.json_body["stream"] is True


def test_build_stream_probe_request_switches_gemini_endpoint() -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://x666.me/v1beta/models/gemini-flash-latest:generateContent",
        headers={"x-goog-api-key": "test-key"},
        json_body={"contents": [{"parts": [{"text": "今天有什么新闻"}]}]},
    )

    streamed = stream_support.build_stream_probe_request(
        request,
        api_dialect="gemini_generate_content",
    )

    assert streamed.url == (
        "https://x666.me/v1beta/models/gemini-flash-latest:streamGenerateContent?alt=sse"
    )
    assert "stream" not in streamed.json_body


def test_execute_stream_probe_request_collects_openai_responses_text(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
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
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"有新闻"}'
            yield ""
            yield "data: [DONE]"
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

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天有新闻"


def test_execute_stream_probe_request_ignores_openai_completed_payload(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
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
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.completed"
            yield 'data: {"output_text":"今天"}'
            yield ""
            yield "data: [DONE]"
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

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天"


def test_flush_stream_event_extracts_openai_chat_truncation_reason() -> None:
    buffer = stream_support.StreamEventBuffer(
        event_name=None,
        data_lines=[
            json_line('{"choices":[{"delta":{"content":"今天"},"finish_reason":"length"}]}'),
        ],
    )

    events = stream_support._flush_stream_event(
        buffer,
        api_dialect="openai_chat_completions",
    )

    assert len(events) == 1
    assert events[0].delta == "今天"
    assert events[0].stop_reason == "length"
    assert stream_support.extract_stream_truncation_reason(events[0].stop_reason) == "length"


def test_flush_stream_event_extracts_gemini_max_tokens_reason() -> None:
    buffer = stream_support.StreamEventBuffer(
        event_name=None,
        data_lines=[
            json_line(
                '{"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"今天"}]}}]}'
            ),
        ],
    )

    events = stream_support._flush_stream_event(
        buffer,
        api_dialect="gemini_generate_content",
    )

    assert len(events) == 1
    assert events[0].delta == "今天"
    assert events[0].stop_reason == "MAX_TOKENS"
    assert stream_support.extract_stream_truncation_reason(events[0].stop_reason) == "MAX_TOKENS"


def test_iterate_stream_request_stops_when_callback_requests_interrupt(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
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
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            await asyncio.sleep(1)
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"还有后续"}'
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

    stop_checks = {"count": 0}

    async def should_stop() -> bool:
        stop_checks["count"] += 1
        return stop_checks["count"] > 4

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    async def collect() -> list[str]:
        parts: list[str] = []
        with pytest.raises(stream_support.StreamInterruptedError):
            async for event in stream_support.iterate_stream_request(
                request,
                api_dialect="openai_responses",
                should_stop=should_stop,
            ):
                parts.append(event.delta)
        return parts

    assert asyncio.run(collect()) == ["今天"]


def json_line(value: str) -> str:
    return value
