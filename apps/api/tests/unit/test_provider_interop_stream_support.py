from __future__ import annotations

import asyncio

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
