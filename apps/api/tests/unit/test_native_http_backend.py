from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm import native_http_backend as native_http_backend_module
from app.shared.runtime.llm.interop.provider_tool_conformance_support import build_text_probe_request
from app.shared.runtime.llm.interop.stream_event_normalizer import ParsedStreamEvent, parse_raw_stream_event
from app.shared.runtime.llm.llm_protocol_types import LLMConnection
from app.shared.runtime.llm.native_http_backend import NativeHttpLLMBackend


def _build_request():
    return build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )


def test_generate_stream_accepts_openai_responses_incomplete_terminal(monkeypatch) -> None:
    backend = NativeHttpLLMBackend()

    async def fake_iterate_stream_request(*args, **kwargs):
        yield parse_raw_stream_event(
            "openai_responses",
            event_name="response.incomplete",
            payload={
                "type": "response.incomplete",
                "response": {
                    "id": "resp_123",
                    "output": [
                        {
                            "id": "msg_1",
                            "type": "message",
                            "content": [{"type": "output_text", "text": "半截内容"}],
                        }
                    ],
                    "incomplete_details": {"reason": "content_filter"},
                },
            },
        )

    monkeypatch.setattr(
        native_http_backend_module.stream_support,
        "build_stream_probe_request",
        lambda prepared_request, *, api_dialect: prepared_request,
    )
    monkeypatch.setattr(
        native_http_backend_module.stream_support,
        "iterate_stream_request",
        fake_iterate_stream_request,
    )

    async def collect():
        events = []
        async for event in backend.generate_stream(_build_request()):
            events.append(event)
        return events

    events = asyncio.run(collect())

    assert len(events) == 1
    assert events[0].terminal_response is not None
    assert events[0].terminal_response.content == "半截内容"
    assert events[0].terminal_response.finish_reason == "content_filter"


def test_generate_stream_raises_openai_responses_failed_message(monkeypatch) -> None:
    backend = NativeHttpLLMBackend()

    async def fake_iterate_stream_request(*args, **kwargs):
        yield ParsedStreamEvent(
            event_name="response.failed",
            payload={
                "type": "response.failed",
                "response": {"error": {"message": "上游失败"}},
            },
            delta="",
            stop_reason=None,
            terminal_response=None,
        )

    monkeypatch.setattr(
        native_http_backend_module.stream_support,
        "build_stream_probe_request",
        lambda prepared_request, *, api_dialect: prepared_request,
    )
    monkeypatch.setattr(
        native_http_backend_module.stream_support,
        "iterate_stream_request",
        fake_iterate_stream_request,
    )

    async def collect():
        events = []
        async for event in backend.generate_stream(_build_request()):
            events.append(event)
        return events

    with pytest.raises(ConfigurationError, match="上游失败"):
        asyncio.run(collect())
