from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider


def test_execute_stream_rejects_gemini_stream_without_finish_reason(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield 'data: {"candidates":[{"content":{"parts":[{"text":"只收到半句"}]}}]}'
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

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_parts() -> list[str]:
        parts: list[str] = []
        with pytest.raises(ConfigurationError, match="上游在输出尚未完成时提前停止了这次回复"):
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "继续写",
                    "model": {"provider": "薄荷", "name": "gemini-2.5-flash"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "gemini_generate_content",
                    },
                },
            ):
                if event.delta:
                    parts.append(event.delta)
        return parts

    assert asyncio.run(collect_parts()) == ["只收到半句"]


def test_execute_stream_accepts_gemini_stream_with_finish_reason(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield 'data: {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"完整回复"}]}}]}'
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

    from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)
    provider = LLMToolProvider()

    async def collect_events():
        return [
            event
            async for event in provider.execute_stream(
                "llm.generate",
                {
                    "prompt": "继续写",
                    "model": {"provider": "薄荷", "name": "gemini-2.5-flash"},
                    "credential": {
                        "api_key": "test-key",
                        "api_dialect": "gemini_generate_content",
                    },
                },
            )
        ]

    events = asyncio.run(collect_events())

    assert [event.delta for event in events[:-1]] == ["完整回复"]
    assert events[-1].response == {
        "content": "完整回复",
        "finish_reason": "STOP",
        "model_name": "gemini-2.5-flash",
        "provider": "薄荷",
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "tool_calls": [],
        "provider_response_id": None,
        "output_items": [],
    }
